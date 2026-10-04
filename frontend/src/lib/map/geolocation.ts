export interface GeolocationResult {
  latitude: number;
  longitude: number;
  accuracy: number;
}

export interface GeolocationError {
  code: number;
  message: string;
}

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
