from setuptools import setup

with open('README.rst') as f:
    readme = f.read()


with open('LICENSE') as f:
    license = f.read()


setup(
    name='vmware-vspc',
    version='0.0.1',
    description='Virtual Serial Port Concentrator',
    long_description=readme,
    author='VMware Inc.',
    author_email='rgerganov@vmware.com',
    url='https://github.com/rgerganov/vmware-vspc',
    license=license,
    entry_points = {
        'console_scripts': ['vmware-vspc=vspc.server:main'],
    },
    packages=['vspc'],
    install_requires=['oslo.config', 'oslo.log']
)
