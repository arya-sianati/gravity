import React from 'react';
import { GravityMap } from '../components/map/GravityMap';

export const MapScreen: React.FC = () => {
  return (
    <div className="flex-1 w-full h-full overflow-hidden bg-gray-900">
      <GravityMap />
    </div>
  );
};
