import React, { useState, useEffect } from "react";
import axios from "axios";
import MainDashboard from "./components/MainDashboard";
import FMECAAnalysis from "./components/FMECAAnalysis";
import Login from "./components/Login.jsx";
import UserProfile from "./components/UserProfile.jsx";
import AdminDashboard from "./components/AdminDashboard.jsx";
import "./App.css";
import { URL } from "../config.js";

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentPage, setCurrentPage] = useState("main");
  const [selectedBoard, setSelectedBoard] = useState(null);
  const [boards, setBoards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [userDetails, setUserDetails] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("access_token"));

  // Configure axios defaults
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    }

    const requestInterceptor = axios.interceptors.request.use(
      (config) => {
        const storedToken = localStorage.getItem("access_token");
        if (storedToken) {
          config.headers.Authorization = `Bearer ${storedToken}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    const responseInterceptor = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem("access_token");
          localStorage.removeItem("username");
          setIsAuthenticated(false);
          setUser(null);
          setUserDetails(null);
          window.location.href = "/";
        }
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.request.eject(requestInterceptor);
      axios.interceptors.response.eject(responseInterceptor);
    };
  }, [token]);

  useEffect(() => {
    const storedToken = localStorage.getItem("access_token");
    const storedUsername = localStorage.getItem("username");

    if (storedToken && storedUsername) {
      setToken(storedToken);
      setIsAuthenticated(true);
      setUser(storedUsername);
      verifyTokenAndGetUser();
      fetchBoards();
    } else {
      setLoading(false);
    }
  }, []);

  const verifyTokenAndGetUser = async () => {
    try {
      const storedToken = localStorage.getItem("access_token");
      if (!storedToken) {
        handleLogout();
        return;
      }

      const response = await axios.get(`${URL}/verify-token`, {
        headers: {
          Authorization: `Bearer ${storedToken}`,
          "Cache-Control": "no-cache",
        },
      });
      setUserDetails(response.data);
      setLoading(false);
    } catch (error) {
      console.error("Token verification failed:", error);
      if (error.response?.status === 401) {
        handleLogout();
      } else {
        setLoading(false);
      }
    }
  };

  const handleLogin = (newToken, username) => {
    localStorage.setItem("access_token", newToken);
    localStorage.setItem("username", username);
    setToken(newToken);
    setIsAuthenticated(true);
    setUser(username);
    setLoading(true);
    verifyTokenAndGetUser();
    fetchBoards();
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    axios.defaults.headers.common["Authorization"] = null;
    setIsAuthenticated(false);
    setUser(null);
    setUserDetails(null);
    setToken(null);
    setCurrentPage("main");
    setSelectedBoard(null);
    setBoards([]);
  };

  const fetchBoards = async () => {
    try {
      const storedToken = localStorage.getItem("access_token");
      if (!storedToken) {
        handleLogout();
        return;
      }

      const response = await axios.get(`${URL}/boards`, {
        headers: {
          Authorization: `Bearer ${storedToken}`,
          "Cache-Control": "no-cache",
        },
      });
      setBoards(response.data);
    } catch (error) {
      console.error("Error fetching boards:", error);
      if (error.response?.status === 401) {
        handleLogout();
      }
    }
  };

  const handleBoardSelect = async (boardId) => {
    try {
      await axios.get(`${URL}/verify-token`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          "Cache-Control": "no-cache",
        },
      });

      setSelectedBoard(boardId);
      setCurrentPage("analysis");
    } catch (error) {
      console.error("Token expired, logging out:", error);
      handleLogout();
    }
  };

  const handleBackToBoards = () => {
    setCurrentPage("main");
    setSelectedBoard(null);
  };

  const handleProfileClick = async () => {
    try {
      await axios.get(`${URL}/verify-token`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          "Cache-Control": "no-cache",
        },
      });

      setCurrentPage("profile");
    } catch (error) {
      console.error("Token expired, logging out:", error);
      handleLogout();
    }
  };

  const handleAdminClick = async () => {
    try {
      await axios.get(`${URL}/verify-token`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          "Cache-Control": "no-cache",
        },
      });

      if (userDetails?.role === "admin") {
        setCurrentPage("admin");
      }
    } catch (error) {
      console.error("Token expired, logging out:", error);
      handleLogout();
    }
  };

  if (!isAuthenticated) {
    return <Login onLogin={handleLogin} />;
  }

  if (loading) {
    return (
      <div className="app-container">
        <div className="loading-screen">Loading...</div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <nav className="navbar">
        <div className="navbar-brand">FMECA-HWATM Integrations</div>
        <div className="navbar-user">
          <span>Welcome, {userDetails?.full_name || user}</span>
          {userDetails?.role === "admin" && (
            <span className="user-role">({userDetails?.role})</span>
          )}
          <button className="profile-button" onClick={handleProfileClick}>
            Profile
          </button>
          {userDetails?.role === "admin" && (
            <button className="admin-button" onClick={handleAdminClick}>
              Admin
            </button>
          )}
          <button className="logout-button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      {currentPage === "main" ? (
        <MainDashboard boards={boards} onBoardSelect={handleBoardSelect} />
      ) : currentPage === "analysis" ? (
        <FMECAAnalysis
          boardId={selectedBoard}
          boardName={boards.find((b) => b.id === selectedBoard)?.name}
          onBack={handleBackToBoards}
        />
      ) : currentPage === "profile" ? (
        <UserProfile
          user={userDetails}
          onBack={() => setCurrentPage("main")}
          onLogout={handleLogout}
        />
      ) : (
        <AdminDashboard onBack={() => setCurrentPage("main")} />
      )}
    </div>
  );
}

export default App;
