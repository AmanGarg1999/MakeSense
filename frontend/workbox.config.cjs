const { generateSW } = require('workbox-build');
const path = require('path');

const config = {
  swDest: path.join(__dirname, 'dist', 'sw.js'),
  globDirectory: path.join(__dirname, 'dist'),
  globPatterns: [
    '**/*.{js,css,html,png,svg,ico,json,woff,woff2}',
  ],
  maximumFileSizeToCacheInBytes: 5 * 1024 * 1024, // 5 MB
  runtimeCaching: [
    {
      urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
      handler: 'CacheFirst',
      options: {
        cacheName: 'google-fonts-cache',
        expiration: {
          maxEntries: 10,
          maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
        },
        cacheableResponse: {
          statuses: [0, 200],
        },
      },
    },
    {
      urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
      handler: 'CacheFirst',
      options: {
        cacheName: 'gstatic-fonts-cache',
        expiration: {
          maxEntries: 10,
          maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
        },
        cacheableResponse: {
          statuses: [0, 200],
        },
      },
    },
    {
      urlPattern: /\/api\/.*/i,
      handler: 'NetworkFirst',
      options: {
        cacheName: 'api-cache',
        networkTimeoutSeconds: 10,
        expiration: {
          maxEntries: 100,
          maxAgeSeconds: 60 * 60 * 24, // 1 day
        },
        cacheableResponse: {
          statuses: [0, 200],
        },
        plugins: [
          {
            fetchDidFail: async ({ request, error }) => {
              console.log('API request failed, will retry when online:', request.url);
            },
          },
        ],
      },
    },
    {
      urlPattern: /.*/i,
      handler: 'StaleWhileRevalidate',
      options: {
        cacheName: 'default-cache',
        expiration: {
          maxEntries: 200,
          maxAgeSeconds: 60 * 60 * 24 * 7, // 1 week
        },
      },
    },
  ],
  // Don't cache these
  navigateFallback: '/index.html',
  navigateFallbackDenylist: [
    /^\/api/,
    /\.json$/,
  ],
  // Skip waiting and claim clients immediately
  skipWaiting: true,
  clientsClaim: true,
  // Cleanup outdated caches
  cleanupOutdatedCaches: true,
};

generateSW(config)
  .then(({ count, size, warnings }) => {
    if (warnings.length > 0) {
      console.warn('Workbox warnings:', warnings);
    }
    console.log(`Generated service worker: ${count} files, ${size} bytes`);
  })
  .catch((error) => {
    console.error('Workbox build failed:', error);
    process.exit(1);
  });