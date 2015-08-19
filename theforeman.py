#!/usr/bin/env python

"""
TheForeman external inventory script
"""

import argparse
import ConfigParser
import os
import urllib
import urllib2
import base64
import ssl

try:
  import json
except:
  import simplejson as json

class TheForemanInventory(object):

  def _empty_inventory(self):
    return {"_meta" : {"hostvars" : {}}}

  def __init__(self):
    ''' Main execution path '''

    # TheForemanInventory data
    self.inventory = self._empty_inventory()

    # Read settings, environment variables, and CLI arguments
    self.read_settings()
    self.read_cli_args()

    # Generate inventory from TheForeman
    self.generate_inventory_from_theforeman()

    # Return JSON inventory for Ansible
    print json.dumps(self.inventory, sort_keys=True, indent=2)

  def read_settings(self):
    ''' Reads the settings from theforeman.ini file '''

    config = ConfigParser.SafeConfigParser()
    config.read(os.path.dirname(os.path.realpath(__file__)) + '/theforeman.ini')
    self.theforeman_host     = config.get('theforeman', 'host')
    self.theforeman_username = config.get('theforeman', 'username')
    self.theforeman_password = config.get('theforeman', 'password')

    # Allow verification of the server if required
    if config.has_option('theforeman', 'cacert'):
      self.theforeman_cacert = config.get('theforeman', 'cacert')

    # Allow mutual verfication of the client
    if config.has_option('theforeman', 'cert'):
      self.theforeman_cert = config.get('theforeman', 'cert')
      self.theforeman_key = config.get('theforeman', 'key')

  def read_cli_args(self):
    ''' Command line argument processing '''

    parser = argparse.ArgumentParser(description='Produce an Ansible Inventory file based on TheForeman inventory')
    parser.add_argument('--list', action='store_true', default=True, help='List hosts (default: True)')
    parser.add_argument('--host', action='store', help='Get all information about a specific host')
    self.args = parser.parse_args()

  def fetch_data_from_theforeman(self):
    ''' Fetch all JSON data from the foreman API '''

    if hasattr(self, 'theforeman_cacert'):
      ssl_context = ssl.create_default_context()
      ssl_context.load_verify_locations(cafile=self.theforeman_cacert)
      if hasattr(self, 'theforeman_cert'):
        ssl_context.load_cert_chain(self.theforeman_cert, keyfile=self.theforeman_key)
    else:
      ssl_context = None
      ssl._create_default_https_context = ssl._create_unverified_context

    # Build the Foreman query
    # TODO: Add support for pagination.
    url = 'https://' + self.theforeman_host + '/api/v2/hosts?per_page=1000'
    base64string = base64.encodestring('%s:%s' % (self.theforeman_username, self.theforeman_password)).replace('\n', '')

    # Fire off the query
    request = urllib2.Request(url)
    request.add_header("Authorization", "Basic %s" % base64string)

    # Return the JSON inventory
    response = urllib2.urlopen(request, context=ssl_context)
    data = json.load(response)
    return data['results']

  def generate_inventory_from_theforeman(self):
    ''' Converts the foreman inventory into ansible '''

    data = self.fetch_data_from_theforeman()

    if self.args.host:
      try:
        self.inventory = [host for host in data if host['name'] == self.args.host][0]
      except IndexError:
        self.inventory = {}
    else:
      for host in data:
        self.inventory.setdefault(host['hostgroup_name'], []).append(host['name'])
        self.inventory['_meta']['hostvars'][host['name']] = host

TheForemanInventory()
