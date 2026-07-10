# Chronos frontend (Vite/React). Build context: ./Frontend
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 5173

# Serve the production build. The app talks to the backend at http://localhost:8000
# (the browser resolves localhost -> the published backend port).
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
