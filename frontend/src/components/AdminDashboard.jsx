import React, { useState, useEffect } from "react";
import axios from "axios";
import UserManagement from "./UserManagement";
import FileUpload from "./FileUpload";
import "./AdminDashboard.css";
import { URL } from "../../config";

function AdminDashboard({ onBack }) {
  const [activeTab, setActiveTab] = useState("users");
  const [stats, setStats] = useState({
    totalUsers: 0,
    adminUsers: 0,
    regularUsers: 0,
    totalBoards: 9,
    boardsWithDbData: 0,
    latestUpload: null,
  });
  const [loading, setLoading] = useState(true);
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

      // Count boards with MongoDB data
      const boardsWithDbData = boards.filter(
        (b) => b.has_fmeca_db || b.has_coverage_db
      ).length;

      // Find latest upload
      let latestUpload = null;
      boards.forEach((board) => {
        if (
          board.last_updated &&
          (!latestUpload ||
            new Date(board.last_updated) > new Date(latestUpload))
        ) {
          latestUpload = board.last_updated;
        }
      });

      setStats({
        totalUsers: users.length,
        adminUsers: adminCount,
        regularUsers: userCount,
        totalBoards: boards.length || 9,
        boardsWithDbData: boardsWithDbData,
        latestUpload: latestUpload,
        fmecaCount: boards.filter((b) => b.has_fmeca_db).length,
        coverageCount: boards.filter((b) => b.has_coverage_db).length,
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

      // Show success message with details
      const message =
        fileType === "image"
          ? `✅ Image uploaded successfully!`
          : `✅ Upload successful! ${
              response.data.record_count
            } records saved to MongoDB.\nVersion: ${
              response.data.version || "1.0"
            }`;

      alert(message);
      setRefreshKey((old) => old + 1); // Refresh stats
    } catch (error) {
      console.error("Upload failed:", error);
      const errorMsg = error.response?.data?.detail || error.message;
      alert(`❌ Upload failed: ${errorMsg}`);
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
      // Return default status if endpoint doesn't exist
      return {
        fmeca_in_db: false,
        coverage_in_db: false,
        fmeca_info: null,
        coverage_info: null,
      };
    }
  };

  const handleRefresh = () => {
    setRefreshKey((old) => old + 1);
  };

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleString();
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
            <p className="admin-subtitle">MongoDB System Management</p>
          </div>
        </div>
        <button className="refresh-button" onClick={handleRefresh}>
          <span className="refresh-icon">↻</span>
          Refresh
        </button>
      </div>

      <div className="dashboard-grid">
        <div className="stats-section">
          <h3 className="section-title">MongoDB Overview</h3>
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
              <div className="stat-icon">📊</div>
              <div className="stat-content">
                <div className="stat-value">{stats.totalBoards}</div>
                <div className="stat-label">Total Boards</div>
                <div className="stat-subtext">Available in system</div>
              </div>
            </div>

            <div className="stat-card stat-card-info">
              <div className="stat-icon">💾</div>
              <div className="stat-content">
                <div className="stat-value">{stats.boardsWithDbData}</div>
                <div className="stat-label">Boards in MongoDB</div>
                <div className="stat-subtext">
                  {Math.round(
                    (stats.boardsWithDbData / stats.totalBoards) * 100
                  )}
                  % complete
                </div>
              </div>
            </div>

            <div className="stat-card stat-card-warning">
              <div className="stat-icon">📁</div>
              <div className="stat-content">
                <div className="stat-value">
                  {stats.fmecaCount}/{stats.coverageCount}
                </div>
                <div className="stat-label">Files in MongoDB</div>
                <div className="stat-subtext">
                  {stats.fmecaCount} FMECA, {stats.coverageCount} Coverage
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mongo-info-section">
          <div className="section-header">
            <h3 className="section-title">MongoDB Storage</h3>
            <div className="mongo-badge">
              <span className="mongo-icon">🍃</span>
              MongoDB Active
            </div>
          </div>
          {stats.latestUpload && (
            <div className="latest-upload">
              <span className="latest-label">Latest Upload:</span>
              <span className="latest-date">
                {formatDate(stats.latestUpload)}
              </span>
            </div>
          )}
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
              <span className="tab-icon">💾</span>
              <span className="tab-text">MongoDB Upload</span>
            </button>
          </div>

          <div className="tab-content-wrapper">
            {activeTab === "users" ? (
              <UserManagement onUpdate={fetchDashboardStats} />
            ) : (
              <FileUpload
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
