import React from "react";

function MainDashboard({ boards, onBoardSelect }) {
  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">FMECA-Hardware Integrations</h1>
      <h3 className="dashboard-subtitle">
        Select a Board to View FMECA Analysis
      </h3>

      <div className="board-grid">
        {boards.map((board) => (
          <div
            key={board.id}
            className="board-item"
            onClick={() => onBoardSelect(board.id)}
          >
            <div
              className={`board-image ${
                board.image ? "has-image" : "no-image"
              }`}
              style={
                board.image ? { backgroundImage: `url(${board.image})` } : {}
              }
            >
              {!board.image && board.name}
            </div>
            <div className="board-name">{board.name}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default MainDashboard;
