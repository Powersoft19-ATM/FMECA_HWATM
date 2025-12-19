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
  const [showAddBoardForm, setShowAddBoardForm] = useState(false);
  const [newBoardData, setNewBoardData] = useState({
    name: "",
    description: "",
    image_path: "",
    category: "main" // or could be "subsystem", "component", etc.
  });
  const [addingBoard, setAddingBoard] = useState(false);

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
      
      const dbStatus = await onGetDbStatus(boardId);
      
      setBoardStatus({
        ...response.data,
        ...dbStatus
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
      await onUploadToDatabase(selectedBoard, selectedFileType, selectedFile);

      setSelectedFile(null);
      document.getElementById("file-input").value = "";

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

  const handleAddBoard = async () => {
    if (!newBoardData.name.trim()) {
      alert("Please enter a board name");
      return;
    }

    if (!newBoardData.image_path.trim()) {
      alert("Please enter the CDN image path");
      return;
    }

    setAddingBoard(true);

    try {
      const response = await axios.post(
        `${URL}/boards`,
        newBoardData,
        {
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
        }
      );

      alert(`✅ Board "${newBoardData.name}" added successfully!`);
      
      // Reset form
      setNewBoardData({
        name: "",
        description: "",
        image_path: "",
        category: "main"
      });
      setShowAddBoardForm(false);
      
      // Refresh boards list and select the new board
      await fetchBoards();
      if (response.data.id) {
        setSelectedBoard(response.data.id);
      }
    } catch (error) {
      console.error("Error adding board:", error);
      alert(
        `❌ Failed to add board: ${error.response?.data?.detail || error.message}`
      );
    } finally {
      setAddingBoard(false);
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

  const validateImageUrl = (url) => {
    // Basic URL validation
    try {
      new URL(url);
      return true;
    } catch (e) {
      return false;
    }
  };

  if (loading) {
    return <div className="loading-message">Loading file upload...</div>;
  }

  return (
    <div className="file-upload-container">
      <div className="upload-form">
        <h3>Upload Files to MongoDB Database</h3>

        <div className="form-group">
          <div className="board-selection-header">
            <label>Select Board:</label>
            <button 
              className="add-board-button"
              onClick={() => setShowAddBoardForm(true)}
            >
              <span className="add-icon">+</span>
              Add New Board
            </button>
          </div>
          
          {showAddBoardForm ? (
            <div className="add-board-form">
              <h4>Add New Board</h4>
              
              <div className="form-input-group">
                <label>Board Name *</label>
                <input
                  type="text"
                  value={newBoardData.name}
                  onChange={(e) => setNewBoardData({...newBoardData, name: e.target.value})}
                  placeholder="Enter board name (e.g., Main Control Board)"
                  className="board-input"
                />
              </div>

              <div className="form-input-group">
                <label>Description</label>
                <input
                  type="text"
                  value={newBoardData.description}
                  onChange={(e) => setNewBoardData({...newBoardData, description: e.target.value})}
                  placeholder="Enter board description"
                  className="board-input"
                />
              </div>

              <div className="form-input-group">
                <label>Board Image CDN Path *</label>
                <input
                  type="url"
                  value={newBoardData.image_path}
                  onChange={(e) => setNewBoardData({...newBoardData, image_path: e.target.value})}
                  placeholder="https://cdn.example.com/board-image.jpg"
                  className="board-input"
                />
                <small className="input-hint">
                  Enter the full URL to the board image (JPG, PNG, or SVG)
                </small>
                
                {newBoardData.image_path && validateImageUrl(newBoardData.image_path) && (
                  <div className="image-preview">
                    <p className="preview-label">Image Preview:</p>
                    <img 
                      src={newBoardData.image_path} 
                      alt="Board preview" 
                      className="preview-image"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.nextElementSibling?.style.display = 'block';
                      }}
                    />
                    <div className="preview-fallback" style={{display: 'none'}}>
                      ⚠️ Image cannot be loaded. Please check the URL.
                    </div>
                  </div>
                )}
              </div>

              <div className="form-input-group">
                <label>Category</label>
                <select
                  value={newBoardData.category}
                  onChange={(e) => setNewBoardData({...newBoardData, category: e.target.value})}
                  className="board-input"
                >
                  <option value="main">Main Board</option>
                  <option value="subsystem">Subsystem</option>
                  <option value="component">Component</option>
                  <option value="module">Module</option>
                </select>
              </div>

              <div className="form-buttons">
                <button
                  className="cancel-button"
                  onClick={() => setShowAddBoardForm(false)}
                  disabled={addingBoard}
                >
                  Cancel
                </button>
                <button
                  className="save-board-button"
                  onClick={handleAddBoard}
                  disabled={addingBoard || !newBoardData.name.trim() || !newBoardData.image_path.trim()}
                >
                  {addingBoard ? "Adding..." : "Save Board"}
                </button>
              </div>
            </div>
          ) : (
            <select
              value={selectedBoard}
              onChange={(e) => setSelectedBoard(e.target.value)}
              className="board-select"
            >
              <option value="">-- Select a Board --</option>
              {boards.map((board) => (
                <option key={board.id} value={board.id}>
                  {board.name} {board.category ? `(${board.category})` : ''}
                </option>
              ))}
            </select>
          )}
        </div>

        {selectedBoard && !showAddBoardForm && (
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
              <div className="status-item">
                <span className="status-label">Board Image:</span>
                <span className="status-value">
                  {getStatusIcon(boardStatus.has_image)}
                </span>
              </div>
            </div>
            
            {boards.find((b) => b.id == selectedBoard)?.image_path && (
              <div className="current-board-image">
                <p className="image-label">Current Board Image:</p>
                <img 
                  src={boards.find((b) => b.id == selectedBoard).image_path} 
                  alt="Board"
                  className="board-thumbnail"
                />
                <a 
                  href={boards.find((b) => b.id == selectedBoard).image_path} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="image-link"
                >
                  View Full Image
                </a>
              </div>
            )}
          </div>
        )}

        {!showAddBoardForm && (
          <>
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
                <strong>Note:</strong> Excel files will be converted to JSON and stored in MongoDB database for faster queries and better data management.
              </p>
              <p className="db-info">
                💡 MongoDB storage allows versioning, faster queries, and better data management.
              </p>
            </div>
          </>
        )}
      </div>

      <div className="database-info">
        <h4>MongoDB Database Benefits</h4>
        <p>
          Storing your Excel data in MongoDB provides these advantages:
        </p>
        <ul>
          <li>⚡ Faster data retrieval and queries</li>
          <li>📊 Version history tracking</li>
          <li>🔍 Advanced search capabilities</li>
          <li>📈 Scalability for large datasets</li>
          <li>✅ Data validation and consistency</li>
          <li>🔄 Real-time data updates</li>
          <li>🔗 Better relationships between data</li>
          <li>📝 Structured JSON storage</li>
        </ul>

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