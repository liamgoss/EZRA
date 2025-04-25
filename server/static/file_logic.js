document.addEventListener("DOMContentLoaded", () => {
    const uploadForm = document.getElementById("uploadForm");
    const fileInput = document.getElementById("fileUpload");
    const dropZone = document.getElementById("dropZone");
    const confirmUpload = document.getElementById("confirmUpload");
    const deleteAfterDownload = document.getElementById("deleteAfterDownload");
    const expirySelect = document.getElementById("expiryHours");
    const modal = document.getElementById("uploadOptionsModal");
  
    window.pendingFiles = [];
  
    // Show selected files
    fileInput.addEventListener("change", () => {
      const files = Array.from(fileInput.files);
      dropZone.textContent = files.length > 0
        ? `Selected: ${files.map(f => f.name).join(', ')}`
        : 'Drag and drop a file here or click to upload';
    });
  
    // Drag/drop behavior
    dropZone.addEventListener("click", () => fileInput.click());
    dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    });
    dropZone.addEventListener("dragleave", () => {
      dropZone.classList.remove("dragover");
    });
    dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
      fileInput.files = e.dataTransfer.files;
  
      const names = Array.from(fileInput.files).map(f => f.name).join(', ');
      dropZone.textContent = `Selected: ${names}`;
    });
  
    
  
    // Upload submit shows modal
    uploadForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const files = Array.from(fileInput.files);
      const errorEl = document.getElementById("uploadError");
      const maxFiles = 5;
      const maxFileSize = 50 * 1024 * 1024; // 50MB
      const maxTotalSize = 250 * 1024 * 1024; // 250MB
    
      errorEl.classList.add("hidden");
    
      if (files.length > maxFiles) {
        errorEl.textContent = `You can only upload up to ${maxFiles} files.`;
        errorEl.classList.remove("hidden");
        return;
      }
      
      if (!files || files.length === 0) {
        errorEl.textContent = "Please select at least one file to upload.";
        errorEl.classList.remove("hidden");
        return;
      }
      
      // Check each file size
      for (const file of files) {
        if (file.size > maxFileSize) {
          errorEl.textContent = `${file.name} exceeds the 50MB file size limit.`;
          errorEl.classList.remove("hidden");
          return;
        }
      }

      const totalSize = files.reduce((sum, file) => sum + file.size, 0);
      if (totalSize > maxTotalSize) {
        errorEl.textContent = `Total upload size exceeds 250MB.`;
        errorEl.classList.remove("hidden");
        return;
      }
    
      window.pendingFiles = files;
      modal.classList.remove("hidden");
    });
    
  
    // ******************* //
    // Core upload handler //
    // ******************* //
    confirmUpload.addEventListener("click", async () => {
      if (pendingFiles.length === 0) return alert("No file selected");
      const stageText = document.getElementById("uploadStage");
      const progressBar = document.getElementById("uploadProgress");
      confirmUpload.disabled = true;
      confirmUpload.textContent = "Encrypting & Uploading...";
    
      try {
        stageText.textContent = "Encrypting your files…";
        const zipData = await createZipArchive(pendingFiles);
    
        // Generate AES key and secret
        const aesKey = new Uint8Array(32);
        const secret = new Uint8Array(32);
        crypto.getRandomValues(aesKey);
        crypto.getRandomValues(secret);
        
    
        // Encrypt with AES-GCM
        const iv = crypto.getRandomValues(new Uint8Array(12));
        const keyObj = await crypto.subtle.importKey('raw', aesKey, { name: 'AES-GCM' }, false, ['encrypt']);
        const ciphertext = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, keyObj, zipData);

        stageText.textContent = "Uploading to EZRA…";
    
        const encryptedBlob = new Blob([iv, new Uint8Array(ciphertext)], { type: 'application/octet-stream' });
    
        const formData = new FormData();
        formData.append("file", encryptedBlob, "encrypted.ezra");
        formData.append("secret", btoa(String.fromCharCode(...secret)));
    
        const expireHours = parseInt(expirySelect.value);
        if (isNaN(expireHours) || expireHours < 1 || expireHours > 72) {
          alert("Please enter a valid expiration between 1 and 72 hours.");
          return;
        }
    
        formData.append("expire_hours", expireHours);
        formData.append("delete_after_download", deleteAfterDownload.checked);
    
        const { proof, public: publicSignals } = await generateProof(btoa(String.fromCharCode(...secret)));
        formData.append("zk_proof", JSON.stringify(proof));
        formData.append("zk_public", JSON.stringify(publicSignals));
    
        // Return composite key *now*, but defer showing it
        const composite = new Uint8Array(secret.length + aesKey.length);
        composite.set(secret, 0);
        composite.set(aesKey, secret.length);
        const compositeB64 = btoa(String.fromCharCode(...composite));
    
        // Setup upload progress
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/upload", true);
    
        xhr.upload.onprogress = function (e) {
          if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            progressBar.value = percent;
            if (percent === 100) {
              stageText.textContent = "Finalizing…";
            }
          }
        };
    
        xhr.onload = async function () {
          if (xhr.status !== 200) {
            alert(`Upload failed: ${xhr.responseText}`);
            return;
          }
          modal.classList.add("hidden");
          // Upload succeeded — now show the secret
          window.showSecretModal(compositeB64);
        };
    
        xhr.onerror = function () {
          alert("Upload failed due to network error.");
        };
    
        xhr.send(formData);
    
      } catch (err) {
        console.error("[Upload Error]", err);
        alert("Upload failed. Check console for more info.");
      } finally {
        
        window.pendingFiles = [];
        confirmUpload.disabled = false;
        confirmUpload.textContent = "Submit";
      }
    });
    
  
    // Zip helper
    async function createZipArchive(files) {
      const zip = new JSZip();
      for (const file of files) {
        const content = await file.arrayBuffer();
        zip.file(file.name, content);
      }
      const blob = await zip.generateAsync({ type: "uint8array" });
      return blob;
    }


    // ********************* //
    // Core download handler //
    // ********************* //
    const downloadBtn = document.querySelector("#downloadForm button");

    document.getElementById("downloadForm").addEventListener("submit", async (e) => {
      e.preventDefault();

      downloadBtn.disabled = true;
      downloadBtn.textContent = "Proving & Decrypting…";

      const secretInput = document.getElementById("downloadSecret");
      const downloadStatus = document.getElementById("downloadStatus");
      const downloadProgress = document.getElementById("downloadProgress");
      const secret = secretInput.value.trim();

      resetDownloadStatus();

      if (!secret) {
        downloadStatus.textContent = "You must enter a secret.";
        downloadStatus.classList.remove("hidden");
        downloadBtn.disabled = false;
        downloadBtn.textContent = "Download";
        return;
      }

      try {
        const secretBytes = Uint8Array.from(atob(secret), c => c.charCodeAt(0));
        const key = secretBytes.slice(32);
        const seed = secretBytes.slice(0, 32);

        const secretB64 = btoa(String.fromCharCode(...seed));
        const { proof, public: publicSignals } = await generateProof(secretB64);

        const res = await fetch("/download", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ proof, public: publicSignals })
        });

        if (!res.ok) {
          const error = await res.text();
          downloadStatus.textContent = `Download failed: ${error}`;
          downloadStatus.classList.remove("hidden");
          return;
        }

        // --- Stream and decode the response ---
        downloadProgress.classList.remove("hidden");

        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        const contentLength = +res.headers.get("Content-Length") || 1;
        let received = 0;
        let text = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          text += decoder.decode(value, { stream: true });
          received += value.length;
          downloadProgress.value = Math.round((received / contentLength) * 100);
        }

        const parsed = JSON.parse(text);
        const ciphertext = parsed.ciphertext;
        const raw = Uint8Array.from(atob(ciphertext), c => c.charCodeAt(0));

        const iv = raw.slice(0, 12);
        const encrypted = raw.slice(12);

        const keyObj = await crypto.subtle.importKey("raw", key, { name: "AES-GCM" }, false, ["decrypt"]);
        const decrypted = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, keyObj, encrypted);

        const blob = new Blob([decrypted], { type: "application/zip" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "ezra_files.zip";
        a.click();

        resetDownloadStatus();
      } catch (err) {
        console.error("[Download Error]", err);
        downloadStatus.textContent = "Download or decryption failed.";
        downloadStatus.classList.remove("hidden");
      } finally {
        downloadProgress.classList.add("hidden");
        downloadProgress.value = 0;
        downloadBtn.disabled = false;
        downloadBtn.textContent = "Download";
      }
    });


});