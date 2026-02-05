/**
 * Simple test map to verify Leaflet works
 */
import React from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';

const SimpleMap = () => {
  const ukCenter = [54.5, -2.5];

  const testNodes = [
    { name: 'London', lat: 51.51, lng: -0.13 },
    { name: 'Manchester', lat: 53.48, lng: -2.24 },
    { name: 'Edinburgh', lat: 55.95, lng: -3.19 },
    { name: 'Birmingham', lat: 52.49, lng: -1.90 },
    { name: 'Cardiff', lat: 51.48, lng: -3.18 },
  ];

  return (
    <div style={{ height: '100vh', width: '100vw', background: '#1e293b' }}>
      <MapContainer
        center={ukCenter}
        zoom={6}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {testNodes.map((node, i) => (
          <CircleMarker
            key={i}
            center={[node.lat, node.lng]}
            radius={10}
            pathOptions={{ color: '#3b82f6', fillColor: '#3b82f6', fillOpacity: 0.8 }}
          >
            <Popup>{node.name}</Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
};

export default SimpleMap;
