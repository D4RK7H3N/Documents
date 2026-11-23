import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.darkzhub.sms',
  appName: 'DarkZ Management',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
};

export default config;
