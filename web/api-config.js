// REQUIRED on Netlify: the Python API is not on the same host as this static site.
//
// 1) Deploy the API (Dockerfile in repo root):
//    - Render: https://render.com → New → Blueprint → connect repo, or New → Web Service → Docker
//    - Copy the public HTTPS URL (e.g. https://gutsafe-api.onrender.com)
//
// 2) Paste it below (no trailing slash), commit, redeploy Netlify.
//
window.__GUTSAFE_API__ = "";
