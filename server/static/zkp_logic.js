document.addEventListener("DOMContentLoaded", () => {
    /**
     * Converts a base64 string into a decimal string representing a BigInt.
     */
    function base64ToBigIntDecimal(b64) {
      const binary = atob(b64);
      const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
      const hex = [...bytes].map(b => b.toString(16).padStart(2, "0")).join("");
      return BigInt("0x" + hex).toString();
    }
  
    /**
     * Fetch the Poseidon hash of the secret from the server.
     */
    async function computePoseidonHash(secretB64) {
      const res = await fetch("/poseidon", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ secret_b64: secretB64 })
      });
  
      if (!res.ok) throw new Error("Failed to compute Poseidon hash");
  
      const data = await res.json();
      return data.hash;
    }
  
    /**
     * Generates a Zero-Knowledge Proof from a base64 secret using snarkjs.
     * Relies on static WASM and ZKey files being served via Flask.
     */
    window.generateProof = async function(secretB64) {
      const secretInt = base64ToBigIntDecimal(secretB64);
      const expected = await computePoseidonHash(secretB64);
  
      const input = {
        x: secretInt,
        expected: expected
      };
  
      const { proof, publicSignals } = await snarkjs.groth16.fullProve(
        input,
        "/static/poseidon_preimage.wasm",
        "/static/poseidon_preimage.zkey"
      );
  
      return { proof, public: publicSignals };
    };
  });
  