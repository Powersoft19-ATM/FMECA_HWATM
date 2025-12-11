import React, { useState, useEffect } from "react";
import axios from "axios";
import UserManagement from "./UserManagement";
import FileUpload from "./FileUpload";
import "./AdminDashboard.css"; // CSS file for styling
import { URL } from "../../config";

function AdminDashboard({ onBack }) {
  const [activeTab, setActiveTab] = useState("users");
  const [stats, setStats] = useState({
    totalUsers: 0,
    adminUsers: 0,
    regularUsers: 0,
    totalBoards: 9,
    boardsWithFiles: 0,
    boardsWithDbData: 0,
  });
  const [loading, setLoading] = useState(true);
  const [uploadMode, setUploadMode] = useState("file"); // "file" or "db"
  const [refreshKey, setRefreshKey] = useState(0);

  const token = localStorage.getItem("access_token");

  useEffect(() => {
    fetchDashboardStats();
  }, [refreshKey]);

  const fetchDashboardStats = async () => {
    try {
      const [usersRes, boardsRes] = await Promise.all([
        axios.get(`${URL}/admin/users`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        axios.get(`${URL}/boards`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ]);

      const users = usersRes.data;
      const boards = boardsRes.data;

      const adminCount = users.filter((u) => u.role === "admin").length;
      const userCount = users.filter((u) => u.role === "user").length;
      const boardsWithFiles = boards.filter(
        (b) => b.has_fmeca && b.has_coverage
      ).length;
      const boardsWithDbData = boards.filter(
        (b) => b.has_fmeca_db && b.has_coverage_db
      ).length;

      setStats({
        totalUsers: users.length,
        adminUsers: adminCount,
        regularUsers: userCount,
        totalBoards: 9,
        boardsWithFiles: boardsWithFiles,
        boardsWithDbData: boardsWithDbData,
      });
      setLoading(false);
    } catch (error) {
      console.error("Error fetching dashboard stats:", error);
      setLoading(false);
    }
  };

  const handleUploadToDatabase = async (boardId, fileType, file) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("file_type", fileType);

    try {
      const response = await axios.post(
        `${URL}/upload/board/${boardId}/excel-to-db`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
            Authorization: `Bearer ${token}`,
          },
        }
      );
      alert(
        `✅ Upload successful! ${response.data.record_count} records saved to database.\nVersion: ${response.data.version}`
      );
      setRefreshKey((old) => old + 1); // Refresh stats with key change
    } catch (error) {
      console.error("Upload failed:", error);
      alert(
        "❌ Upload failed: " + (error.response?.data?.detail || error.message)
      );
    }
  };

  const getBoardDbStatus = async (boardId) => {
    try {
      const response = await axios.get(`${URL}/board/${boardId}/db-status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      return response.data;
    } catch (error) {
      console.error("Error getting DB status:", error);
      return null;
    }
  };

  const handleRefresh = () => {
    setRefreshKey((old) => old + 1);
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
        <div className="loading-message">Loading admin dashboard...</div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      <div className="admin-header">
        <div className="header-left">
          <button className="back-button" onClick={onBack}>
            <span className="back-arrow">←</span>
            Back to Main
          </button>
          <div className="header-titles">
            <h2 className="admin-title">Admin Dashboard</h2>
            <p className="admin-subtitle">System Management & Monitoring</p>
          </div>
        </div>
        <button className="refresh-button" onClick={handleRefresh}>
          <span className="refresh-icon">↻</span>
          Refresh
        </button>
      </div>

      <div className="dashboard-grid">
        <div className="stats-section">
          <h3 className="section-title">Overview</h3>
          <div className="stats-grid">
            <div className="stat-card stat-card-primary">
              <div className="stat-icon">👥</div>
              <div className="stat-content">
                <div className="stat-value">{stats.totalUsers}</div>
                <div className="stat-label">Total Users</div>
                <div className="stat-subtext">
                  {stats.adminUsers} admin, {stats.regularUsers} regular
                </div>
              </div>
            </div>

            <div className="stat-card stat-card-success">
              <div className="stat-icon">🛡️</div>
              <div className="stat-content">
                <div className="stat-value">{stats.adminUsers}</div>
                <div className="stat-label">Admin Users</div>
                <div className="stat-subtext">System administrators</div>
              </div>
            </div>

            <div className="stat-card stat-card-info">
              <div className="stat-icon">👤</div>
              <div className="stat-content">
                <div className="stat-value">{stats.regularUsers}</div>
                <div className="stat-label">Regular Users</div>
                <div className="stat-subtext">Standard access users</div>
              </div>
            </div>

            <div className="stat-card stat-card-warning">
              <div className="stat-icon">📊</div>
              <div className="stat-content">
                <div className="stat-value">
                  {stats.boardsWithDbData}/{stats.totalBoards}
                </div>
                <div className="stat-label">Boards in Database</div>
                <div className="stat-subtext">
                  {Math.round(
                    (stats.boardsWithDbData / stats.totalBoards) * 100
                  )}
                  % complete
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="upload-mode-section">
          <div className="section-header">
            <h3 className="section-title">Upload Configuration</h3>
            <div className="mode-badge">
              {uploadMode === "db" ? "Database Storage" : "File Storage"}
            </div>
          </div>
          <div className="upload-mode-selector">
            <div className="mode-options">
              <button
                className={`mode-button ${uploadMode === "db" ? "active" : ""}`}
                onClick={() => setUploadMode("db")}
              >
                <span className="mode-icon">💾</span>
                <span className="mode-text">Database Mode</span>
                <span className="mode-description">
                  Store data in MongoDB with version control
                </span>
              </button>
            </div>
            <div className="mode-info">
              <div className="info-icon">ℹ️</div>
              <div className="info-text">
                {uploadMode === "file"
                  ? "Files are stored directly in the file system"
                  : "Excel files are parsed and stored in MongoDB database with audit trail"}
              </div>
            </div>
          </div>
        </div>

        <div className="tabs-section">
          <div className="admin-tabs">
            <button
              className={`tab-button ${activeTab === "users" ? "active" : ""}`}
              onClick={() => setActiveTab("users")}
            >
              <span className="tab-icon">👥</span>
              <span className="tab-text">User Management</span>
            </button>
            <button
              className={`tab-button ${activeTab === "files" ? "active" : ""}`}
              onClick={() => setActiveTab("files")}
            >
              <span className="tab-icon">📁</span>
              <span className="tab-text">File Upload</span>
            </button>
          </div>

          <div className="tab-content-wrapper">
            {activeTab === "users" ? (
              <UserManagement onUpdate={fetchDashboardStats} />
            ) : (
              <FileUpload
                uploadMode={uploadMode}
                onUploadToDatabase={handleUploadToDatabase}
                onGetDbStatus={getBoardDbStatus}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AdminDashboard;
