/**
 * API client for Telecom RAG backend.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

export async function askTelecomAI(question) {
  const url = `${BASE_URL}/api/chat`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    let errorMsg = 'Failed to get answer from server.';
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
