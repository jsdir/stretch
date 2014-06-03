var _ = require('lodash');
var async = require('async');
var nconf = require('nconf');
var Chance = require('chance');
var pkgcloud = require('pkgcloud');
var winston = require('winston');

var chance = new Chance();

var createClient = function(options) {
  return pkgcloud.compute.createClient({
    provider: 'rackspace',
    username: options.username,
    apiKey: options.apiKey,
    region: options.region.toUpperCase()
  });
};

var getRackspaceInfo = function(client, flavorName, imageId, cb) {
  async.series([
    function(callback) {
      winston.debug('Finding flavors matching: ' + flavorName);
      client.getFlavors(function(err, flavors) {
        if (err) {
          callback(err);
        } else {
          var flavor = _.findWhere(flavors, {name: flavorName});
          callback(null, flavor);
        }
      });
    },
    function(callback) {
      winston.debug('Finding image with id: ' + imageId);
      client.getImage(imageId, callback);
    }
  ], function(err, results) {
    if (err) {
      throw(err);
    } else {
      cb(results);
    }
  });
};

var createHostWithImage = function() {

};

module.exports = {

  etcdHost: '172.17.42.1:4001',

  createHost: function(options, service, cb) {
    /*
    Create a fully provisioned host.
      1. Create host on rackspace. (with image containing fleet)
      2. Distribute encryption keys to the server.
      3. Modify service configuration to use the keys.
      4. Restart services (fleet).
    */

    var client = createClient(options);

    var flavorName = options.flavorName || '512MB Standard Instance';
    var imageId = options.coreosImageId || '430d35e0-1468-4007-b063-52ee1921b356';

    var saveBuiltImages = config.saveBuiltImages || true;

    // Make image name from version.
    var version = require('..');
    var imageName = config.imageName || ('stretch-'
      + require('../../package.json').version + '-host-image');

    // Get flavor and image.
    winston.info('Finding specified flavor and image');
    getRackspaceInfo(client, flavorName, imageId, function(results) {
      var flavor = results[0],
          image  = results[1];

      winston.info('Found flavor: ' + flavor.name);
      winston.info('Found image matching id: ' + imageId);

      // Create a host on rackspace.
      var hostHashLength = options.hostHashLength || 16;
      var name = service.name + '-' + chance.hash({length: hostHashLength});
      client.createServer({
        name: name,
        flavor: flavor,
        image: image
      }, function(err, callback){

      });
    });

    client.createImage({
      name: 'imageName',  // required
      server: 'serverId'  // required
    }, callback);
  },

  destroyHost: function() {

  }
};