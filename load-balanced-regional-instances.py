# Function that will generate an external load balancer and use this with the regional instances
# created by a regional instance group manager
# Adapted from the following:  https://cloud.google.com/deployment-manager/docs/create-advanced-http-load-balanced-deployment
COMPUTE_URL_BASE = 'https://www.googleapis.com/compute/v1/'


def GenerateConfig(context):
    resources = [{
        # Creates the regional IGM utilising the VM-template below and creates this in a specific zone
        # It also dynamically creates how many VMs it requires by using the targetSize
        "name": context.env['name'] + "-igm",
        "type": "compute.v1.regionInstanceGroupManager",
        "properties": {
            "instanceTemplate": "$(ref." + context.env['name'] +  "-template.selfLink)",
            "namedPorts": [{
                "name": "http",
                "port": 80
            }],
            "targetSize": context.properties['targetSize'],
            "region": context.properties["region"],
            "zone": context.properties["zone"]
        }
    },{
        # Instance template code for creating a specific Linux instance, utilising the URL_BASE variable
        "name": context.env['name'] + "-template",
        "type": "compute.v1.instanceTemplate",
        "properties": {
            "properties": {
                'machineType': context.properties['machineType'],
                'canIpForward': False,
                'disks': [{
                    "type": "PERSISTENT",
                    "boot": True,
                    "initializeParams": {
                        "sourceImage": ''.join([COMPUTE_URL_BASE, 'projects/',
                                                'debian-cloud/global/',
                                                'images/family/debian-9'])
                    }
                }],
                'networkInterfaces': [{
                    "network": COMPUTE_URL_BASE + 'projects/' + context.env['project'] + '/global/networks/default',
                    "accessConfigs": [{
                        "name": "External NAT",
                        "type": "ONE_TO_ONE_NAT"
                        }]
                }]
            }
        }
    }, {
        # Creates a backend service for the IGM. 
        # Health checking is created to ensure traffic works correctly
        # The type of service is defined at the end of this service ('HTTP')
        "name": context.env['name'] + "-bs",
        "type": "compute.v1.backendService",
        "properties":{
            "backends": [{
                "group": "$(ref." + context.env['name'] + "-igm.instanceGroup)",
            }],
            "healthChecks": [
                "$(ref." + context.env['name'] + "-hc.selfLink)",
            ],
            "loadBalancingScheme": "EXTERNAL",
            "portName": "http",
            "protocol": "HTTP",
        }
    }, {
        # This is the creation of the health check that is used above
        "name": context.env['name'] + "-hc",
        "type": "compute.v1.httpHealthCheck"
    }, {
        # Due to default firewall implications from Google,
        # a firewall will be created here
        "name": context.env['name'] + "-allowed-hc",
        "type": "compute.v1.firewall",
        "properties": {
            "sourceRanges": [
                "35.191.0.0/16",
                "130.211.0.0/22"
            ],
            "allowed": [{
                "IPProtocol": "tcp",
                "ports": [
                    "80"
                ]
            }]
        }
    }, {
        # The URL Mapper will essentially be the 'router'
        # This will be able to link the requests to the correct service
        # For instance, /api will be redirected to the correct part if it is there
        "name": context.env['name'] + "-url-map",
        "type": "compute.v1.urlMap",
        "properties": {
            "defaultService": "$(ref." + context.env['name'] + "-bs.selfLink)",
        }
    }, {
        # Target proxy will encrypt the data transferred,
        # this will use a SSL self-signed certificate
        "name": context.env['name'] + "-target-proxy",
        "type": "compute.v1.targetHttpsProxy",
        "properties": {
            "sslCertificates": [
                "$(ref." + context.env['name'] + "-ssl-cert.selfLink)"
            ],
            "urlMap": "$(ref." + context.env['name'] + "-url-map.selfLink)"
        }
    }, {
        # The SSL self-signed certificate keys are below.
        # Help from https://cloud.google.com/load-balancing/docs/ssl-certificates
        "name": context.env['name'] + "-ssl-cert",
        "type": "compute.v1.sslCertificate",
        "properties": {
            "certificate": """-----BEGIN CERTIFICATE-----
MIIDmjCCAoICCQDIuHI3qmilITANBgkqhkiG9w0BAQsFADCBjjELMAkGA1UEBhMC
R0IxEDAOBgNVBAgMB0xpbmNvbG4xEDAOBgNVBAcMB0xpbmNvbG4xCzAJBgNVBAoM
AklUMRAwDgYDVQQLDAdTdHVkZW50MQwwCgYDVQQDDANKb2UxLjAsBgkqhkiG9w0B
CQEWHzE0NTg3NTA2QHN0dWRlbnRzLmxpbmNvbG4uYWMudWswHhcNMTkxMTA0MTYw
MzI5WhcNMjAxMTAzMTYwMzI5WjCBjjELMAkGA1UEBhMCR0IxEDAOBgNVBAgMB0xp
bmNvbG4xEDAOBgNVBAcMB0xpbmNvbG4xCzAJBgNVBAoMAklUMRAwDgYDVQQLDAdT
dHVkZW50MQwwCgYDVQQDDANKb2UxLjAsBgkqhkiG9w0BCQEWHzE0NTg3NTA2QHN0
dWRlbnRzLmxpbmNvbG4uYWMudWswggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEK
AoIBAQDMkUcwcGwZTJMFUVKgTXa3PdkSJruVU/TLSebS4EKgXeQCVUMnoTj0WY5l
FiYnos5XVcnamZvsTwNtjzy1+++cMTUak7EGcKyvaibGNTysZD4TJk3WY3/r8KtC
klkx3EYLqU3i7A1PRxWLY3/hNN/+gbpYpFDSTCwgxkKMAKCJanqKF7HHVeVFEB0Q
71cbKOjuEPpLHEJU4WvRnk1QyZM2/6ZGNKVYNlI5O44m6lUrvUAMB9cPrMViXEW9
pPN6b3i4L4XcmTv1533PPq75bbjxDCWk50c99ydCmo9+cLfvslxCCaEz7J6WHjSk
pN1idr/4WKFeGGk7XhZEJFDz/wEVAgMBAAEwDQYJKoZIhvcNAQELBQADggEBAA6+
wf6frS4fy4vHGykprrYlOS1uxQVNZPGRPoRhJDW7cfuYUCgWehH+7EcDlCAI9ket
CZ2anWPH2GPxnxbQ9ORNF9x1hHz+FxiJn04hR6fKTMBg9uTwSr7aBcby+7ez8pvJ
byXfQIut88Dww1XW2RYGmvS+yCN/YDHhNeI1hD/0IoCVM8JIOBY52bJLqkIwayGa
S/V8KuEVb4AaG0igHQJzKYz8xhJc4RHrfWatI2hPbZdxGUE1M0x121vUF6LTP2tW
ui9SWaqThKMvZ0oI8IGDPrRE1OMDytbfdaW1jSUQ7czVxk3B3sXCqOjX5VKrkchK
AkKSkaY4VRsk3BE+o5E=
-----END CERTIFICATE-----
""",
            "privateKey": """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDMkUcwcGwZTJMF
UVKgTXa3PdkSJruVU/TLSebS4EKgXeQCVUMnoTj0WY5lFiYnos5XVcnamZvsTwNt
jzy1+++cMTUak7EGcKyvaibGNTysZD4TJk3WY3/r8KtCklkx3EYLqU3i7A1PRxWL
Y3/hNN/+gbpYpFDSTCwgxkKMAKCJanqKF7HHVeVFEB0Q71cbKOjuEPpLHEJU4WvR
nk1QyZM2/6ZGNKVYNlI5O44m6lUrvUAMB9cPrMViXEW9pPN6b3i4L4XcmTv1533P
Pq75bbjxDCWk50c99ydCmo9+cLfvslxCCaEz7J6WHjSkpN1idr/4WKFeGGk7XhZE
JFDz/wEVAgMBAAECggEBAKqU5lENHgcGpH5Frum/TqREbZNGOxutU66E5HapzMUf
JfeQE5yjQvP3DddbXdulVfzbq6OefbfSt2APlieGeuq62bZcu7xMDqODl+umDv8N
4/lh8nw4oj4jhRvRH5GFRd+JgUodXofiFaQTB1rLFZGLqdEqy75hCFcYG/vUtgl/
Aw+qY999h5zPBqUoTRZmZs30XWHjS4r+CVmx88MeSextlHCE5QGQ8dbDxcpOjo4o
1c4NDizNqvk7Hzz4If0WTprVZjBnuRWMEn6dEkP/6EACtzVMTqFp1YgBURn2se+x
ClkLCkllOGikCRMgEXXCrXUyR90o4thLJNC67HJBZk0CgYEA9qdp8VBWBahzKZpC
djM2eLUParCJtcGfWtwZkaJfkVCdCZM9un8qt/+MpPWlrGSVu5IQd44nH43zEOyH
zPjcbODHw+DJ4yNpc3QnN+vt2RVtbt/RG8bA/U/Y1ALRaKqr+6d+x9+pEgfGfw6p
S0oXsJQvbWUg5h0LFrSRupvKZV8CgYEA1FGeQzVIxuZWqKvCd816Rt3klz4xLlZE
xH8GLkpeRc/FY4szkHpmr0+05SBAsAHi1Gcj42RxGSIOHEi0tgSEZkKFC3XCqfSa
jL1FK/TFAGatgaJajurrdhqeDOurnu5xR+Iszqfs9BGabl9Lvf09CAS+q0+vtrd7
Z9/iRgKfGgsCgYEA1DWrV5v3trx8AIIgxlM/fVDB59flU0Q311NgiET8FikWQwO0
az03wsCR/+b82Dpd/NgpZMMf8+0MADaQjBBcjSxDkspWyB5SfqujhmBs7YWa9naI
EW7J4ecNtTKLepLEjypHUK2kZ8faxrwVeZpQkXKc73C/glvgi3NlofihhN8CgYAE
os+Y2hX/udHUlwOFCCiOWZP/NW1vfJS90aQ56IfMcG/373ctxW5uj4f8pMqkzTW9
u47ODUhm6xZxyaigfNLDRNqQ2H5qpZumTQ+wmQSgMJ3DQd9GVZzUlFo1IAQ8USqK
Dkc6L/J9ldDQbiZCPMBTZ38eUHweujzolLvlGXON5wKBgCI3iDkEnZbTYvbKOFAA
63oe0D4Cr4VLToqVk1JM5K+rUIotp0kK38YZ+B+Uh0cM0pHNOtH+GjRB76z1a83g
Q/fnl53rKj9/dDkchcF8nrr99ICrgseZ4tcYKrYCSqAd4ahk02Cf2W4CFwcm8eFg
WgyPULOGAkK/Z9uSEkHzmYoX
-----END PRIVATE KEY-----
"""
            }
    }, {
        # The entry point for this whole area.
        # This takes in the relevant IPs, etc.
        "name": context.env['name'] + "-fr",
        "type": "compute.v1.globalForwardingRule",
        "properties": {
            "IPAddress": "$(ref." + context.env['name'] + "-static-ip.selfLink)",
            "IPProtocol": "TCP",
            "loadBalancingScheme": "EXTERNAL",
            "portRange": "443",
            "target": "$(ref." + context.env['name'] + "-target-proxy.selfLink)"
        }
    }, {
        # Auto-selected (by Google) external IP
        "name": context.env['name'] + "-static-ip",
        "type": "compute.v1.globalAddress"
    }]
    return {'resources': resources}
