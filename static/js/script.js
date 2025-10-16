document.addEventListener('DOMContentLoaded', () => {
  const uploadArea = document.getElementById('uploadArea');
  const fileInput = document.getElementById('fileInput');
  const cameraInput = document.getElementById('cameraInput');
  const cameraModal = document.getElementById('cameraModal');
  const cameraVideo = document.getElementById('cameraVideo');
  const captureBtn = document.getElementById('captureBtn');
  const closeCameraBtn = document.getElementById('closeCameraBtn');
  const cameraCanvas = document.getElementById('cameraCanvas');
  let cameraStream = null;

  const uploadContent = document.getElementById('uploadContent');
  const imagePreview = document.getElementById('imagePreview');
  const previewContainer = document.getElementById('previewContainer');
  const chooseFileBtn = document.getElementById('chooseFileBtn');
  const cameraBtn = document.getElementById('cameraBtn');
  const removeImgBtn = document.getElementById('removeImgBtn');

  function stopCamera() {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      cameraStream = null;
    }
    if (cameraVideo) cameraVideo.srcObject = null;
  }

  function handleFiles(files) {
    if (!files || !files.length) return;
    previewContainer.innerHTML = ''; // clear old
    Array.from(files).forEach(file => {
      if (!file.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = e => {
        const img = document.createElement('img');
        img.src = e.target.result;
        img.className = "w-full h-32 object-cover rounded-lg shadow";
        previewContainer.appendChild(img);
      };
      reader.readAsDataURL(file);
    });
    uploadContent.classList.add('hidden');
    imagePreview.classList.remove('hidden');
  }

  // Choose file button
  if (chooseFileBtn) {
    chooseFileBtn.addEventListener('click', e => {
      e.stopPropagation();
      fileInput.value = '';
      fileInput.click();
    });
  }

  // Camera button
  if (cameraBtn) {
    cameraBtn.addEventListener('click', async e => {
      e.stopPropagation();
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('เบราว์เซอร์ของคุณไม่รองรับการเปิดกล้อง');
        return;
      }
      try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        cameraVideo.srcObject = cameraStream;
        cameraModal.classList.remove('hidden');
      } catch (err) {
        alert('ไม่สามารถเข้าถึงกล้องได้ หรือคุณไม่ได้อนุญาต');
      }
    });
  }

  // Capture photo
  if (captureBtn) {
    captureBtn.addEventListener('click', () => {
      if (!cameraVideo.srcObject) return;
      const width = cameraVideo.videoWidth;
      const height = cameraVideo.videoHeight;
      cameraCanvas.width = width;
      cameraCanvas.height = height;
      const ctx = cameraCanvas.getContext('2d');
      ctx.drawImage(cameraVideo, 0, 0, width, height);
      cameraCanvas.toBlob(blob => {
        if (blob) {
          const file = new File([blob], 'capture.jpg', { type: 'image/jpeg' });
          handleFiles([file]);
        }
      }, 'image/jpeg');
      stopCamera();
      cameraModal.classList.add('hidden');
    });
  }

  if (closeCameraBtn) {
    closeCameraBtn.addEventListener('click', () => {
      stopCamera();
      cameraModal.classList.add('hidden');
    });
  }

  // Drag & drop
  if (uploadArea) {
    uploadArea.addEventListener('dragover', e => {
      e.preventDefault();
      uploadArea.classList.add('dragover');
    });
    uploadArea.addEventListener('dragleave', e => {
      e.preventDefault();
      uploadArea.classList.remove('dragover');
    });
    uploadArea.addEventListener('drop', e => {
      e.preventDefault();
      uploadArea.classList.remove('dragover');
      if (e.dataTransfer.files.length) {
        handleFiles(e.dataTransfer.files);
      }
    });
  }

  // File input
  if (fileInput) {
    fileInput.addEventListener('change', e => {
      if (e.target.files.length) {
        handleFiles(e.target.files);
      }
    });
  }

  // Camera input
  if (cameraInput) {
    cameraInput.addEventListener('change', e => {
      if (e.target.files.length) {
        handleFiles(e.target.files);
      }
    });
  }

  // Remove/change
  if (removeImgBtn) {
    removeImgBtn.addEventListener('click', () => {
      previewContainer.innerHTML = '';
      imagePreview.classList.add('hidden');
      uploadContent.classList.remove('hidden');
      fileInput.value = '';
      cameraInput.value = '';
    });
  }
});

// Toggle mobile menu
function toggleMobileMenu() {
  const menu = document.getElementById('mobileMenu');
  if (menu) menu.classList.toggle('hidden');
}
