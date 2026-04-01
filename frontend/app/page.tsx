'use client';

import { useState } from 'react';

export default function Home() {
  const [inputText, setInputText] = useState('');
  const [status, setStatus] = useState('');

  const handleSave = async () => {
    setStatus('Saving...');
    try {
      // Calling the FastAPI backend on port 8000
      const response = await fetch('http://localhost:8000/api/save-dummy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: inputText }),
      });

      if (response.ok) {
        const data = await response.json();
        setStatus(`Success! Saved with ID: ${data.saved_id}`);
      } else {
        setStatus('Failed to save to database.');
      }
    } catch (error) {
      console.error('Error:', error);
      setStatus('Network error. Is FastAPI running?');
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-4">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-2xl font-bold mb-6 text-gray-800">Phase 0: Scaffold Test</h1>
        
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Enter a dummy string..."
          className="w-full p-3 border border-gray-300 rounded mb-4 text-black"
        />
        
        <button
          onClick={handleSave}
          className="w-full bg-blue-600 text-white font-bold py-3 rounded hover:bg-blue-700 transition"
        >
          Save to PostgreSQL
        </button>

        {status && (
          <p className="mt-4 text-center font-medium text-gray-700">
            {status}
          </p>
        )}
      </div>
    </div>
  );
}