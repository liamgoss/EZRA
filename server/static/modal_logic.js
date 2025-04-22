document.addEventListener("DOMContentLoaded", () => {
    // Modal elements
    const secretModal = document.getElementById("secretModal");
    const secretMessage = document.getElementById("secretMessage");
    const copySecretBtn = document.getElementById("copySecret");
    const closeSecretModalBtn = document.getElementById("closeSecretModal");
  
    const uploadOptionsModal = document.getElementById("uploadOptionsModal");
    const cancelUpload = document.getElementById("cancelUpload");
  
    let currentSecret = "";
  
    // Reset UI after secret modal closes
    window.resetUploadUI = function () {
        const fileInput = document.getElementById("fileUpload");
        const dropZone = document.getElementById("dropZone");
        const uploadForm = document.getElementById("uploadForm");
        const responseMsg = document.getElementById("responseMsg");
      
        if (fileInput) fileInput.value = "";
        if (dropZone) dropZone.textContent = "Drag and drop a file here or click to upload";
        if (uploadForm) uploadForm.reset();
        if (responseMsg) {
          responseMsg.textContent = "";
          responseMsg.classList.add("hidden");
        }
      
        window.pendingFiles = [];
      };

  
    // Show modal with secret
    window.showSecretModal = function(secret) {
      currentSecret = secret;
      secretMessage.innerHTML = `This is your secret:<br><br><strong>${secret}</strong><br><br>Copy and share it securely. You won't be able to retrieve it again.`;
  
      let countdown = 5;
      closeSecretModalBtn.disabled = true;
      closeSecretModalBtn.textContent = `Close (${countdown})`;
      secretModal.classList.remove("hidden");
  
      const timer = setInterval(() => {
        countdown--;
        if (countdown > 0) {
          closeSecretModalBtn.textContent = `Close (${countdown})`;
        } else {
          clearInterval(timer);
          closeSecretModalBtn.disabled = false;
          closeSecretModalBtn.textContent = "Close";
        }
      }, 1000);
    };
  
    // Copy to clipboard handler
    copySecretBtn.addEventListener("click", () => {
      const tempInput = document.createElement("textarea");
      tempInput.value = currentSecret;
      document.body.appendChild(tempInput);
      tempInput.select();
      document.execCommand("copy");
      document.body.removeChild(tempInput);
  
      copySecretBtn.textContent = "Copied!";
      setTimeout(() => {
        copySecretBtn.textContent = "Copy to Clipboard";
      }, 2000);
    });
  
    // Close modal handler
    closeSecretModalBtn.addEventListener("click", () => {
      secretModal.classList.add("hidden");
      secretMessage.textContent = "";
      currentSecret = "";
      resetUploadUI();
    });
  
    // Cancel upload modal
    cancelUpload.addEventListener("click", () => {
      uploadOptionsModal.classList.add("hidden");
      window.pendingFiles = [];
    });

    
    // Download modal
    window.resetDownloadStatus = function () {
        const downloadStatus = document.getElementById("downloadStatus");
        downloadStatus.classList.add("hidden");
        downloadStatus.textContent = "";
        document.getElementById("downloadSecret").value = "";
      };
  });
  
  