# CropGuard AI (UC-031) — Google Cloud Run Deployment Guide

This guide walks you through deploying **CropGuard AI** as a live, publicly accessible website using **Google Cloud Run (Option A: Unified Container)**.

---

## ⚡ Deployment Method 1: Google Cloud Console (Recommended — No CLI Needed)

This is the easiest method. Google Cloud automatically builds the Dockerfile from your GitHub repository and assigns you a live `https://*.run.app` URL with free SSL.

### Step 1: Open Google Cloud Run
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. In the top search bar, type **Cloud Run** and click on it.
3. Make sure your target Google Cloud Project is selected in the top bar.

### Step 2: Create Service
1. Click **Create Service** (or **Deploy Container**).
2. Choose **"Continuously deploy from a repository"** and click **Set up with Cloud Build**.
3. Select **GitHub** as your repository provider.
4. Authorize Google Cloud and select your repository: `purnalokesh31-hub/UC-031`.
5. Select branch: `^main$`.
6. Under **Build Type**, select **Dockerfile**. Source location: `/Dockerfile`.
7. Click **Save**.

### Step 3: Configure Service Settings
- **Service Name:** `cropguard-ai`
- **Region:** `asia-south1` (Mumbai) or `us-central1` (Iowa)
- **Authentication:** Select **"Allow unauthenticated invocations"** (public website).
- **Container Scaling & Resources (under *Container, Volumes, Networking, Security*):**
  - **Memory:** `2 GiB` (recommended for ONNX vision inference & Qiskit statevectors)
  - **CPU:** `2`
  - **Container Port:** `8080` (automatically picked up from `$PORT`)
  - **Min instances:** `0` (scales to zero when not in use = **$0 cost**)
  - **Max instances:** `10`

### Step 4: Deploy!
Click **Create**. Google Cloud Build will:
1. Download Node.js and build the Vite React frontend.
2. Download Python 3.12 and install the ML & FastAPI dependencies.
3. Bundle the unified container and deploy to Cloud Run.
4. Generate a public URL: **`https://cropguard-ai-XXXXX.run.app`**

---

## 💻 Deployment Method 2: Google Cloud Shell (1 Command)

If you prefer deploying via terminal without installing anything on your PC:

1. Open [Google Cloud Shell](https://shell.cloud.google.com/) in your browser.
2. Clone your repository:
   ```bash
   git clone https://github.com/purnalokesh31-hub/UC-031.git
   cd UC-031
   ```
3. Run the one-line deployment command:
   ```bash
   gcloud run deploy cropguard-ai \
     --source . \
     --region asia-south1 \
     --platform managed \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 2
   ```
4. When prompted, press `Y` to confirm. Cloud Run will build and output your live service URL!

---

## 🌐 Verifying the Live Website

Once deployed, visit your Cloud Run URL:
- **Web App Dashboard:** `https://your-service-url.run.app/`
- **Field Notebook:** `https://your-service-url.run.app/#fields`
- **Disease Diagnostics:** `https://your-service-url.run.app/#disease`
- **Health Endpoint:** `https://your-service-url.run.app/health`
- **Interactive OpenAPI Docs:** `https://your-service-url.run.app/docs`
- **Programmatic Yield API:** `POST https://your-service-url.run.app/yield/predict`
