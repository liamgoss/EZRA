document.addEventListener("DOMContentLoaded", () => {
    const uploadForm = document.getElementById("uploadForm");
    const fileInput = document.getElementById("fileUpload");
    const dropZone = document.getElementById("dropZone");
    const confirmUpload = document.getElementById("confirmUpload");
    const deleteAfterDownload = document.getElementById("deleteAfterDownload");
    const expirySelect = document.getElementById("expiryDays");
    const customExpiryInput = document.getElementById("customExpiry");
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
  
    // Expiry input toggle
    expirySelect.addEventListener("change", () => {
      if (expirySelect.value === "custom") {
        customExpiryInput.classList.remove("hidden");
        customExpiryInput.required = true;
      } else {
        customExpiryInput.classList.add("hidden");
        customExpiryInput.required = false;
      }
    });
  
    // Upload submit shows modal
    uploadForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const files = Array.from(fileInput.files);
      const maxFiles = 5;
  
      if (files.length > maxFiles) {
        alert(`You can only upload up to ${maxFiles} files.`);
        return;
      }
      if (files.length === 0) {
        alert("No files selected.");
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
  
      confirmUpload.disabled = true;
      confirmUpload.textContent = "Encrypting & Uploading...";
  
      try {
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
  
        // Combine IV + ciphertext
        const encryptedBlob = new Blob([iv, new Uint8Array(ciphertext)], { type: 'application/octet-stream' });
  
        // FormData
        const formData = new FormData();
        
        formData.append("file", encryptedBlob, "encrypted.ezra");
        formData.append("secret", btoa(String.fromCharCode(...secret)));
  
        // Expiration
        const selectedValue = expirySelect.value;
        const expireDays = selectedValue === "custom"
          ? parseInt(customExpiryInput.value)
          : parseInt(selectedValue);
        if (isNaN(expireDays) || expireDays < 1 || expireDays > 31) {
          alert("Please enter a valid expiration between 1 and 31 days.");
          return;
        }
  
        formData.append("expire_days", expireDays);
        formData.append("delete_after_download", deleteAfterDownload.checked);

        const { proof, public: publicSignals } = await generateProof(btoa(String.fromCharCode(...secret)));
        formData.append("zk_proof", JSON.stringify(proof));
        formData.append("zk_public", JSON.stringify(publicSignals));

  
        // Upload
        const res = await fetch("/upload", {
          method: "POST",
          body: formData,
        });
  
        if (!res.ok) {
          const error = await res.text();
          alert(`Upload failed: ${error}`);
          return;
        }
  
        const json = await res.json();
  
        // Return composite key
        const composite = new Uint8Array(secret.length + aesKey.length);
        composite.set(secret, 0);
        composite.set(aesKey, secret.length);
        const compositeB64 = btoa(String.fromCharCode(...composite));
  
        window.showSecretModal(compositeB64);
  
      } catch (err) {
        console.error("[Upload Error]", err);
        alert("Upload failed. Check console for more info.");
      } finally {
        modal.classList.add("hidden");
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
    // Download logic
    const downloadBtn = document.querySelector("#downloadForm button");

    document.getElementById("downloadForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    downloadBtn.disabled = true;
    downloadBtn.textContent = "Proving & Decrypting…";

    const secretInput = document.getElementById("downloadSecret");
    const downloadStatus = document.getElementById("downloadStatus");
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

        const { ciphertext } = await res.json();
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
        downloadBtn.disabled = false;
        downloadBtn.textContent = "Download";
    }
    });

});