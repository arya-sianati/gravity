export interface GeolocationResult {
  latitude: number;
  longitude: number;
  accuracy: number;
}

export interface GeolocationError {
  code: number;
  message: string;
}

export const LOCATION_PRIVACY_EXPLANATION =
  'Gravity uses your location to discover nearby activity. Your exact location follows your privacy setting.';

export const formatGeolocationErrorMessage = (err: GeolocationError): string => {
  if (err.code === 1) {
    return 'Location access was denied. Enable location in your browser or system settings to discover activity around you.';
  }
  if (err.code === 2) {
    return 'Location is currently unavailable. Please verify GPS or network connectivity and retry.';
  }
  if (err.code === 3) {
    return 'Location request timed out. Please retry.';
  }
  return 'Unable to determine your location. Check your location settings and retry.';
};

export const requestCurrentLocation = (
  onSuccess: (loc: GeolocationResult) => void,
  onError: (err: GeolocationError) => void
) => {
  if (!navigator.geolocation) {
    onError({ code: 0, message: 'Geolocation is not supported by your browser' });
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      onSuccess({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
      });
    },
    (error) => {
      onError({ code: error.code, message: error.message });
    },
    {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 0,
    }
  );
};
