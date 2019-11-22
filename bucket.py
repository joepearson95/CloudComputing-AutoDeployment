# Imports for creating a random string in order to allow the bucket to be unique
import random
import string

# Function that takes in an integer that specifies the length of the random string generated
def random_string(length):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

# Function to generate the bucket. Uses the random_string function and the name specified
# in the yaml file to generate a name for the bucket itself.
def GenerateConfig(context):
    name = ''.join(random_string(4) + context.env['name'])
    resources = [{
        'name': name,
        'type': 'storage.v1.bucket',
        'properties': {
            'project': context.env['project'],
            'name': name
        }
    }]
    return {'resources': resources}
