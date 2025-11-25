# Frontend

Modern, clean frontend for the Fact-Check Assistant, inspired by modern design aesthetics.

## Features

- 🎨 Clean, modern UI with smooth animations
- 📤 Drag & drop file upload
- 📊 Real-time progress tracking
- 📈 Visual score display with circular progress
- ✅ Claim-by-claim verdict breakdown
- 📱 Responsive design

## Usage

The frontend is automatically served by FastAPI when you run:

```bash
poetry run uvicorn backend.app.main:app --reload
```

Then visit: http://localhost:8000

## Files

- `index.html` - Main HTML structure
- `styles.css` - Styling and animations
- `app.js` - Frontend logic and API integration

## Customization

The frontend connects to the API at `http://localhost:8001` by default. To change this, edit the `API_BASE` constant in `app.js`.

