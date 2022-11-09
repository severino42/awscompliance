import boto3
import pprint
import csv
import operator


def sort_key_func(item):
    """ Helper function used to sort list of dicts

    :param item: dict
    :return: sorted list of tuples (k, v)
    """
    pairs = []
    for k, v in item.items():
        pairs.append((k, v))
    return sorted(pairs)

class aws_data():
    def __init__(self):
        self.session = boto3.session.Session()
        self.ec2client = boto3.client('ec2')
        self.ec2response = self.ec2client.describe_instances()
        self.vol_data = dict()
        self.ec2_data = dict()
        self.vol_ec2_data = dict()
        self.get_vol_data()
        self.get_ec2_data()

    def get_vol_data(self):
        volumes = []
        # Get all Volumes using paginator
        paginator = self.ec2client.get_paginator("describe_volumes")
        page_iterator = paginator.paginate()
        for page in page_iterator:
            volumes.extend(page["Volumes"])
        # Get data to self.vol_data
        for vol in volumes:
            if 'Tags' in vol:
                self.vol_data[vol['VolumeId']] = [vol["Attachments"], ["Encrypted", vol['Encrypted']],vol['Tags']]
            else:
                self.vol_data[vol['VolumeId']] = [vol["Attachments"], ["Encrypted", vol['Encrypted']],['No Volume Tags']]

    def get_ec2_data(self):
        for reservation in self.ec2response["Reservations"]:
            for instance in reservation["Instances"]:
                if 'BlockDeviceMappings' in instance:
                    for BlockDevice in instance['BlockDeviceMappings']:
                        data=list()
                        noCustomerData=False
                        if BlockDevice['Ebs']['VolumeId'] in self.vol_data:
                            data.append(BlockDevice['Ebs']['VolumeId'])
                            data.append(instance['InstanceId'])
                            data.append(self.vol_data[BlockDevice['Ebs']['VolumeId']][1])
                        if 'Tags' in instance: 
                            tags = list()
                            name = False
                            for tag in instance['Tags']:
                                if not name and tag['Key'] == 'Name':
                                    name = True
                                    data.append(tag['Value'])
                                    if str(tag['Value']).find('-ci') > -1:
                                        noCustomerdata=True
                                        data.append(["No Customer Data, CI system"])
                                tags.append({tag['Key']:tag['Value']})
                            if not name:
                                data.append("  ")
                            sorted(tags, key=sort_key_func)
                            data.append(tags)
                        for item in self.vol_data[BlockDevice['Ebs']['VolumeId']][2:]:
                            data.append(item)
                        if 'IamInstanceProfile' in instance:
                            data.append(instance['IamInstanceProfile']['Arn'])
                        if ('NetworkInterfaces' in instance) and (instance['NetworkInterfaces'] != []):
                            for interface in instance['NetworkInterfaces']:
                                if 'Groups' in interface:
                                    for SecurityGroup in interface['Groups']:
                                        data.append([SecurityGroup['GroupId'], SecurityGroup['GroupName']])
                        self.vol_ec2_data[str(BlockDevice['Ebs']['VolumeId'])+str(instance['InstanceId'])]=[data]

    def print_data(self):
        # Print our data by EC2 instance
        for volume in list(self.vol_data):
            pprint.pprint(self.vol_data[volume])
            print("****************")

    def write_csv_data(self):
        header=['VolumeID', 'InstanceID', "Encrypted", "Name Tag", "Instance Tags", "Volume Tags", "Iam Profile", "Security Groups"]
        with open('volumes.csv', 'w') as f:
            write = csv.writer(f)
            write.writerow(header)
            for key in self.vol_ec2_data.keys():
                row = list(self.vol_ec2_data[key])
                write.writerows(row)
            for vol in self.vol_data:
                try: 
                    if  self.vol_data[vol][0][0].get('AttachTime'):
                        i=1 # no-op to skip
                except IndexError: # print out everthing unattached as they are not in self.vol_ec2_data
                    row = list()
                    row.append([[vol], ["Unattached Volume"],self.vol_data[vol]])
                    write.writerows(row)
            

    def write_vol_data(self):
        for vol in self.vol_data:
                try: 
                    if  self.vol_data[vol][0][0].get('AttachTime'):
                        i=1
                except IndexError:
                    pprint.pprint(vol)
                    pprint.pprint(self.vol_data[vol])
            

if __name__ == '__main__':
    import argparse
    # Initialize parser
    parser = argparse.ArgumentParser()    
    # Adding optional argument
    parser.add_argument("--csv", default=False, help = "Print csv file")
    parser.add_argument("--vol", default=False, help = "Print vol_data")
    
    # Read arguments from command line
    args = parser.parse_args()
    
    aws = aws_data()
    if args.csv:
        aws.write_csv_data()
    elif args.vol:
        aws.print_vol_data()
    else:
        aws.print_data()

# Eugene Petrov attests that volumes where " (size < 15 GB) and( has tags) and (tag:Application in (bitc, whodat, howdat)) " have no PHI
# I have asked Eugene to open a tkt to encrypt/remove these volumes so we can be fully encrypted.