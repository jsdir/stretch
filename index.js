#!/usr/bin/env node

/*!
 * Stretch
 * Copyright(c) 2014 Pictalk <jason@pictalk.com>
 * MIT Licensed
 */

'use strict';


var winston = require('winston');

function configureLogger(nconf) {
  var logOptions = {
    label: process.pid,
    timestamp: true,
    prettyPrint: true,
    colorize: true
  };

  if (nconf.get('debug')) {
    logOptions.level = 'debug';
  } else if (nconf.get('verbose')) {
    logOptions.level = 'verbose';
  }

  if (nconf.get('log')) {
    logOptions.filename = nconf.get('log');
    winston.add(winston.transports.File, logOptions);
  }

  winston.add(winston.transports.Console, logOptions);
}

// Remove console transport for now
winston.remove(winston.transports.Console);

/**
 * Stretch CLI
 */
function main() {

  var nconf = require('nconf');

  /*
  Set up stretch for use:

    1. Command line arguments
    2. Environment variables
    3. Config file
    4. Defaults

  (Listed in order of precedence.)
  */

  nconf
    .argv()
    .env()
    .file({file: 'config.yml', format: nconf.formats.yaml});

  configureLogger(nconf);

  console.log('- - - - - - -'.cyan);
  console.log('S t r e t c h'.cyan);
  console.log('- - - - - - -'.cyan);
}

if (require.main === module) {
  main();
}
