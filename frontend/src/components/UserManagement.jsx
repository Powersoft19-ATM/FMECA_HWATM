import React, { useState, useEffect } from "react";
import axios from "axios";
import { URL } from "../../config";
function UserManagement({ onUpdate }) {
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // New user form state
  const [newUser, setNewUser] = useState({
    username: "",
    email: "",
    full_name: "",
    password: "",
    role: "user",
    disabled: false,
  });

  // Edit user form state
  const [editUser, setEditUser] = useState({
    email: "",
    full_name: "",
    role: "user",
    disabled: false,
  });

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    filterUsers();
  }, [users, searchTerm, roleFilter]);

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${URL}/admin/users`);
      setUsers(response.data);
      setFilteredUsers(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Error fetching users:", error);
      setError("Failed to load users");
      setLoading(false);
    }
  };

  const filterUsers = () => {
    let filtered = users;

    if (searchTerm) {
      filtered = filtered.filter(
        (user) =>
          user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
          user.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
          user.full_name?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (roleFilter !== "all") {
      filtered = filtered.filter((user) => user.role === roleFilter);
    }

    setFilteredUsers(filtered);
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      await axios.post(`${URL}/admin/users`, newUser);
      setSuccess("User created successfully!");
      setNewUser({
        username: "",
        email: "",
        full_name: "",
        password: "",
        role: "user",
        disabled: false,
      });
      setShowCreateForm(false);
      fetchUsers();
      onUpdate();
    } catch (error) {
      setError(error.response?.data?.detail || "Failed to create user");
    }
  };

  const handleEditUser = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      await axios.put(`${URL}/admin/users/${selectedUser.username}`, editUser);
      setSuccess("User updated successfully!");
      setShowEditForm(false);
      setSelectedUser(null);
      fetchUsers();
      onUpdate();
    } catch (error) {
      setError(error.response?.data?.detail || "Failed to update user");
    }
  };

  const handleDeleteUser = async (username) => {
    if (
      !window.confirm(`Are you sure you want to delete user "${username}"?`)
    ) {
      return;
    }

    try {
      await axios.delete(`${URL}/admin/users/${username}`);
      setSuccess("User deleted successfully!");
      fetchUsers();
      onUpdate();
    } catch (error) {
      setError(error.response?.data?.detail || "Failed to delete user");
    }
  };

  const handleToggleUserStatus = async (user) => {
    try {
      if (user.disabled) {
        await axios.put(`${URL}/admin/users/${user.username}/enable`);
        setSuccess(`User ${user.username} enabled`);
      } else {
        await axios.put(`${URL}/admin/users/${user.username}/disable`);
        setSuccess(`User ${user.username} disabled`);
      }
      fetchUsers();
      onUpdate();
    } catch (error) {
      setError(error.response?.data?.detail || "Failed to update user status");
    }
  };

  const openEditForm = (user) => {
    setSelectedUser(user);
    setEditUser({
      email: user.email || "",
      full_name: user.full_name || "",
      role: user.role,
      disabled: user.disabled,
    });
    setShowEditForm(true);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };

  if (loading) {
    return <div className="loading-message">Loading users...</div>;
  }

  return (
    <div className="user-management">
      <div className="management-header">
        <h3>User Management</h3>
        <button
          className="create-user-button"
          onClick={() => setShowCreateForm(true)}
        >
          + Create New User
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}

      <div className="filters">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="role-filter">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
          >
            <option value="all">All Roles</option>
            <option value="admin">Admin</option>
            <option value="user">User</option>
          </select>
        </div>
      </div>

      <div className="users-table-container">
        <table className="users-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Full Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => (
              <tr key={user.id}>
                <td>
                  <div className="user-info">
                    <span className="username">{user.username}</span>
                    {user.role === "admin" && (
                      <span className="admin-badge">Admin</span>
                    )}
                  </div>
                </td>
                <td>{user.full_name || "-"}</td>
                <td>{user.email || "-"}</td>
                <td>
                  <span className={`role-badge role-${user.role}`}>
                    {user.role}
                  </span>
                </td>
                <td>
                  <span
                    className={`status-badge ${
                      user.disabled ? "disabled" : "active"
                    }`}
                  >
                    {user.disabled ? "Disabled" : "Active"}
                  </span>
                </td>
                <td>{formatDate(user.created_at)}</td>
                <td>
                  <div className="action-buttons">
                    <button
                      className="edit-button"
                      onClick={() => openEditForm(user)}
                    >
                      Edit
                    </button>
                    <button
                      className="toggle-button"
                      onClick={() => handleToggleUserStatus(user)}
                    >
                      {user.disabled ? "Enable" : "Disable"}
                    </button>
                    {user.role !== "admin" && (
                      <button
                        className="delete-button"
                        onClick={() => handleDeleteUser(user.username)}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filteredUsers.length === 0 && (
          <div className="no-users">No users found</div>
        )}
      </div>

      {/* Create User Modal */}
      {showCreateForm && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>Create New User</h3>
              <button
                className="close-button"
                onClick={() => setShowCreateForm(false)}
              >
                ×
              </button>
            </div>
            <form onSubmit={handleCreateUser} className="modal-form">
              <div className="form-group">
                <label>Username *</label>
                <input
                  type="text"
                  value={newUser.username}
                  onChange={(e) =>
                    setNewUser({ ...newUser, username: e.target.value })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={newUser.email}
                  onChange={(e) =>
                    setNewUser({ ...newUser, email: e.target.value })
                  }
                />
              </div>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={newUser.full_name}
                  onChange={(e) =>
                    setNewUser({ ...newUser, full_name: e.target.value })
                  }
                />
              </div>
              <div className="form-group">
                <label>Password *</label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={(e) =>
                    setNewUser({ ...newUser, password: e.target.value })
                  }
                  required
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={newUser.role}
                  onChange={(e) =>
                    setNewUser({ ...newUser, role: e.target.value })
                  }
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={newUser.disabled}
                    onChange={(e) =>
                      setNewUser({ ...newUser, disabled: e.target.checked })
                    }
                  />
                  Disabled
                </label>
              </div>
              <div className="form-buttons">
                <button type="submit" className="submit-button">
                  Create User
                </button>
                <button
                  type="button"
                  className="cancel-button"
                  onClick={() => setShowCreateForm(false)}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {showEditForm && selectedUser && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>Edit User: {selectedUser.username}</h3>
              <button
                className="close-button"
                onClick={() => {
                  setShowEditForm(false);
                  setSelectedUser(null);
                }}
              >
                ×
              </button>
            </div>
            <form onSubmit={handleEditUser} className="modal-form">
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={editUser.email}
                  onChange={(e) =>
                    setEditUser({ ...editUser, email: e.target.value })
                  }
                />
              </div>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={editUser.full_name}
                  onChange={(e) =>
                    setEditUser({ ...editUser, full_name: e.target.value })
                  }
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={editUser.role}
                  onChange={(e) =>
                    setEditUser({ ...editUser, role: e.target.value })
                  }
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={editUser.disabled}
                    onChange={(e) =>
                      setEditUser({ ...editUser, disabled: e.target.checked })
                    }
                  />
                  Disabled
                </label>
              </div>
              <div className="form-buttons">
                <button type="submit" className="submit-button">
                  Update User
                </button>
                <button
                  type="button"
                  className="cancel-button"
                  onClick={() => {
                    setShowEditForm(false);
                    setSelectedUser(null);
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default UserManagement;
