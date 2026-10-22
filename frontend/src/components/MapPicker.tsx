import { CircleMarker, MapContainer, TileLayer, useMapEvents } from "react-leaflet";

export interface LatLng {
  lat: number;
  lng: number;
}

interface MapPickerProps {
  value: LatLng;
  onChange: (value: LatLng) => void;
  center?: LatLng;
}

function ClickHandler({ onChange }: { onChange: (value: LatLng) => void }) {
  useMapEvents({
    click(event) {
      onChange({ lat: Number(event.latlng.lat.toFixed(6)), lng: Number(event.latlng.lng.toFixed(6)) });
    },
  });
  return null;
}

export default function MapPicker({ value, onChange, center }: MapPickerProps) {
  const initial = center ?? value;
  return (
    <MapContainer
      center={[initial.lat, initial.lng]}
      zoom={16}
      className="h-80 w-full"
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickHandler onChange={onChange} />
      <CircleMarker
        center={[value.lat, value.lng]}
        radius={9}
        pathOptions={{
          color: "#4f46e5",
          fillColor: "#6366f1",
          fillOpacity: 0.85,
          weight: 2,
        }}
      />
    </MapContainer>
  );
}
