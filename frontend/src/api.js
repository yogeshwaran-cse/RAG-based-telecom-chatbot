/**
 * API client for Telecom RAG backend.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

export async function askTelecomAI(question) {
  const url = `${BASE_URL}/api/chat`;
  
  let response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question }),
    });
  } catch (networkErr) {
    throw new Error(
      `Cannot reach backend server. ${BASE_URL ? `Failed to connect to ${BASE_URL}.` : 'Please ensure the backend is running and CORS is enabled.'}`
    );
  }

  if (!response.ok) {
    if ((response.status === 405 || response.status === 404) && !BASE_URL) {
      throw new Error(
        'The backend API is not configured on this frontend. In your Vercel Project Settings > Environment Variables, please add VITE_API_URL pointing to your deployed Python backend (e.g., https://your-backend.onrender.com).'
      );
    }

    let errorMsg = `Server returned error (${response.status}).`;
    try {
      const errorData = await response.json();
      if (errorData?.detail) {
        errorMsg = errorData.detail;
      }
    } catch {
      // Ignore JSON parse error
    }
    throw new Error(errorMsg);
  }

  const data = await response.json();
  return data.answer;
}
