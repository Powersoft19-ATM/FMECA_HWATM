import React, { useState, useEffect } from "react";
import axios from "axios";
import "./FileUpload.css";
import { URL } from "../../config";

function FileUpload({ onUploadToDatabase, onGetDbStatus }) {
  const [boards, setBoards] = useState([]);
  const [selectedBoard, setSelectedBoard] = useState("");
  const [selectedFileType, setSelectedFileType] = useState("fmeca");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [boardStatus, setBoardStatus] = useState({});
  const [loading, setLoading] = useState(true);

  const token = localStorage.getItem("access_token");

  useEffect(() => {
    fetchBoards();
  }, []);

  useEffect(() => {
    if (selectedBoard) {
      fetchBoardStatus(selectedBoard);
    }
  }, [selectedBoard]);

  const fetchBoards = async () => {
    try {
      const response = await axios.get(`${URL}/boards`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setBoards(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching boards:", error);
      setLoading(false);
    }
  };

  const fetchBoardStatus = async (boardId) => {
    try {
      const response = await axios.get(`${URL}/board/${boardId}/files`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      // Get DB status from parent component
      const dbStatus = await onGetDbStatus(boardId);

      // Combine file system status (if any) with DB status
      setBoardStatus({
        ...response.data,
        ...dbStatus,
      });
    } catch (error) {
      console.error("Error fetching board status:", error);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedBoard || !selectedFile) {
      alert("Please select a board and a file");
      return;
    }

    setUploading(true);

    try {
      // Upload to MongoDB database
      await onUploadToDatabase(selectedBoard, selectedFileType, selectedFile);

      // Reset form
      setSelectedFile(null);
      document.getElementById("file-input").value = "";

      // Refresh status
      fetchBoardStatus(selectedBoard);
      fetchBoards();

      alert("✅ File uploaded to MongoDB successfully!");
    } catch (error) {
      console.error("Upload error:", error);
      alert(
        `❌ Upload failed: ${error.response?.data?.detail || error.message}`
      );
    } finally {
      setUploading(false);
    }
  };

  const getFileTypeLabel = (type) => {
    switch (type) {
      case "fmeca":
        return "FMECA Excel";
      case "coverage":
        return "Coverage Excel";
      case "image":
        return "Board Image";
      default:
        return type;
    }
  };

  const getStatusIcon = (status) => {
    return status ? "✅" : "❌";
  };

  if (loading) {
    return <div className="loading-message">Loading file upload...</div>;
  }

  return (
    <div className="file-upload-container">
      <div className="upload-form">
        <h3>Upload Files to MongoDB Database</h3>

        <div className="form-group">
          <label>Select Board:</label>
          <select
            value={selectedBoard}
            onChange={(e) => setSelectedBoard(e.target.value)}
            className="board-select"
          >
            <option value="">-- Select a Board --</option>
            {boards.map((board) => (
              <option key={board.id} value={board.id}>
                {board.name} (ID: {board.id})
              </option>
            ))}
          </select>
        </div>

        {selectedBoard && (
          <div className="board-status">
            <h4>
              Database Status for{" "}
              {boards.find((b) => b.id == selectedBoard)?.name}
            </h4>
            <div className="status-grid">
              <div className="status-item">
                <span className="status-label">FMECA in DB:</span>
                <span className="status-value">
                  {getStatusIcon(boardStatus.fmeca_in_db)}
                </span>
              </div>
              <div className="status-item">
                <span className="status-label">Coverage in DB:</span>
                <span className="status-value">
                  {getStatusIcon(boardStatus.coverage_in_db)}
                </span>
              </div>
            </div>
          </div>
        )}

        <div className="form-group">
          <label>File Type:</label>
          <div className="file-type-buttons">
            {["fmeca", "coverage", "image"].map((type) => (
              <button
                key={type}
                type="button"
                className={`file-type-button ${
                  selectedFileType === type ? "active" : ""
                }`}
                onClick={() => setSelectedFileType(type)}
              >
                {getFileTypeLabel(type)}
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label>Select File:</label>
          <input
            id="file-input"
            type="file"
            accept={selectedFileType === "image" ? "image/*" : ".xlsx,.xls"}
            onChange={handleFileChange}
            className="file-input"
          />
          {selectedFile && (
            <div className="file-info">
              <span className="file-name">{selectedFile.name}</span>
              <span className="file-size">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </span>
            </div>
          )}
        </div>

        <button
          className="upload-button"
          onClick={handleUpload}
          disabled={uploading || !selectedBoard || !selectedFile}
        >
          {uploading ? "Uploading to MongoDB..." : "Upload to MongoDB"}
        </button>

        <div className="upload-info">
          <p>
            <strong>Note:</strong> Excel files will be converted to JSON and
            stored in MongoDB database for faster queries and better data
            management.
          </p>
          <p className="db-info">
            💡 MongoDB storage allows versioning, faster queries, and better
            data management.
          </p>
        </div>
      </div>

      <div className="database-info">
        {selectedBoard && boardStatus.fmeca_in_db && (
          <div className="db-details">
            <h5>MongoDB Details:</h5>
            <div className="db-detail">
              <span>FMECA Version:</span>
              <span>{boardStatus.fmeca_info?.version || "N/A"}</span>
            </div>
            <div className="db-detail">
              <span>FMECA Records:</span>
              <span>{boardStatus.fmeca_info?.record_count || "N/A"}</span>
            </div>
            <div className="db-detail">
              <span>Coverage Records:</span>
              <span>{boardStatus.coverage_info?.record_count || "N/A"}</span>
            </div>
            <div className="db-detail">
              <span>Last Uploaded:</span>
              <span>
                {boardStatus.fmeca_info?.upload_date
                  ? new Date(
                      boardStatus.fmeca_info.upload_date
                    ).toLocaleString()
                  : "N/A"}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default FileUpload;
