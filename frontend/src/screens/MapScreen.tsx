import React from 'react';
import { GravityMap } from '../components/map/GravityMap';

export const MapScreen: React.FC = () => {
  return (
    <div className="flex-1 w-full h-full relative overflow-hidden bg-gray-950">
      <GravityMap />
    </div>
  );
};
