import { useRef, useState } from "react";

const ACCEPTED = ["image/png", "image/jpeg", "image/webp", "image/gif"];
const MAX_BYTES = 20 * 1024 * 1024; // must match backend MAX_UPLOAD_BYTES

function formatSize(bytes) {
  return bytes >= 1024 * 1024 ? `${(bytes / (1024 * 1024)).toFixed(1)} MB` : `${Math.round(bytes / 1024)} KB`;
}

export default function Uploader({ file, previewUrl, disabled, onSelect, onError }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  function accept(f) {
    if (!f) return;
    if (!ACCEPTED.includes(f.type)) {
      onError("Please choose a PNG, JPEG, WEBP or GIF image.");
      return;
    }
    if (f.size > MAX_BYTES) {
      onError("Image is larger than 20 MB.");
      return;
    }
    onSelect(f);
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    if (!disabled) accept(e.dataTransfer.files?.[0]);
  }

  return (
    <div>
      <div
        className={`dropzone ${dragging ? "dragging" : ""} ${previewUrl ? "has-image" : ""} ${disabled ? "disabled" : ""}`}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && !disabled && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        role="button"
        tabIndex={0}
        aria-label="Upload a site photo"
      >
        {previewUrl ? (
          <img src={previewUrl} alt="Selected site photo" className="preview" />
        ) : (
          <div className="dropzone-hint">
            <span className="upload-icon" aria-hidden="true">⬆</span>
            <p><strong>Drop a site photo here</strong> or click to browse</p>
            <p className="muted">PNG, JPEG, WEBP or GIF · up to 20 MB</p>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(",")}
          hidden
          onChange={(e) => {
            accept(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
      </div>
      {file && (
        <p className="file-meta">
          {file.name} · {formatSize(file.size)}
          {!disabled && <span className="muted"> · click the image to change it</span>}
        </p>
      )}
    </div>
  );
}
