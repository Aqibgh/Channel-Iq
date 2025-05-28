module.exports = function override(config, env) {
  if (env === 'production') {
    config.plugins.push(require('babel-plugin-transform-remove-console'));
  }
  return config;
};
