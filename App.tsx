import React from 'react';
import { AppProvider } from './src/utils/store';
import MainNavigator from './src/components/MainNavigator';

export default function App() {
  return (
    <AppProvider>
      <MainNavigator />
    </AppProvider>
  );
}
