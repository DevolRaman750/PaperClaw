'use client';

import { useState } from 'react';

export default function Home() {
  const [inputText, setInputText] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);

  // Helper to ensure our DB has the test skill
  const seedDatabase = async () => {
    await fetch('http://localhost:8000/api/seed-skill', { method: 'POST' });
    alert("Database seeded with 'sarcastic-reviewer' skill!");
  };

  const handleSend = async () => {
    setLoading(true);
    setResponse('Thinking...');
    
    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          skill_name: 'sarcastic-reviewer', // Pulling Layer 1 logic
          user_prompt: inputText 
        }),
      });

      const data = await res.json();
      if (res.ok) {
        setResponse(data.agent_response);
      } else {
        setResponse(`Error: ${data.detail}`);
      }
    } catch (error) {
      setResponse('Network error. Is the backend running?');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-4">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-2xl">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-800">Phase 1: Dumb Pipeline</h1>
          <button onClick={seedDatabase} className="text-xs bg-gray-200 text-gray-700 px-3 py-1 rounded">
            1. Seed Database First
          </button>
        </div>
        
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Ask the sarcastic senior developer a question..."
          className="w-full p-3 border border-gray-300 rounded mb-4 text-black h-32"
        />
        
        <button
          onClick={handleSend}
          disabled={loading}
          className="w-full bg-blue-600 text-white font-bold py-3 rounded hover:bg-blue-700 transition disabled:bg-blue-300"
        >
          {loading ? 'Executing...' : 'Run Agent'}
        </button>

        {response && (
          <div className="mt-6 p-4 bg-gray-100 rounded border border-gray-200">
            <h3 className="text-sm font-bold text-gray-500 mb-2">Agent Response:</h3>
            <p className="text-gray-800 whitespace-pre-wrap">{response}</p>
          </div>
        )}
      </div>
    </div>
  );
}