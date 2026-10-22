
const express = require("express");
const cors = require("cors");
const { initializeDatabase } = require("./database");

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json({ limit: "1mb" }));

// Health check
app.get("/api/health", (req, res) => {
  res.json({
    success: true,
    message: "CivicSense backend is running!",
  });
});

// Start the server only after database initialization
async function startServer() {
  const { db, saveDatabase } = await initializeDatabase();

  // GET all complaints
  app.get("/api/complaints", (req, res) => {
    try {
      const result = db.exec(
        "SELECT * FROM complaints ORDER BY id DESC"
      );

      let complaints = [];

      if (result.length > 0) {
        const { columns, values } = result[0];

        complaints = values.map((row) =>
          Object.fromEntries(
            columns.map((column, index) => [column, row[index]])
          )
        );
      }

      res.json({
        success: true,
        complaints,
      });
    } catch (error) {
      console.error("GET complaints error:", error);
      res.status(500).json({
        success: false,
        message: "Could not retrieve complaints",
      });
    }
  });

  // POST a new complaint
  app.post("/api/complaints", (req, res) => {
    const { title, description, category, location, priority } = req.body;

    if (
      typeof title !== "string" || !title.trim() ||
      typeof description !== "string" || !description.trim() ||
      typeof category !== "string" || !category.trim() ||
      typeof location !== "string" || !location.trim()
    ) {
      return res.status(400).json({
        success: false,
        message: "Title, description, category and location are required",
      });
    }

    const allowedPriorities = ["High", "Medium", "Low"];
    const safePriority = allowedPriorities.includes(priority)
      ? priority
      : "Medium";

    try {
      db.run(
        `INSERT INTO complaints
          (title, description, category, location, priority)
         VALUES (?, ?, ?, ?, ?)`,
        [
          title.trim(),
          description.trim(),
          category.trim(),
          location.trim(),
          safePriority,
        ]
      );

      saveDatabase();

      const result = db.exec(
        "SELECT * FROM complaints ORDER BY id DESC LIMIT 1"
      );

      const { columns, values } = result[0];
      const row = values[0];

      const complaint = Object.fromEntries(
        columns.map((column, index) => [column, row[index]])
      );

      return res.status(201).json({
        success: true,
        complaint,
      });
    } catch (error) {
      console.error("POST complaint error:", error);
      return res.status(500).json({
        success: false,
        message: "Could not save complaint",
      });
    }
  });

  // Start listening for requests
  const server = app.listen(PORT, () => {
    console.log(`CivicSense backend running at http://localhost:${PORT}`);
    console.log("Available endpoints:");
    console.log("GET  /api/health");
    console.log("GET  /api/complaints");
    console.log("POST /api/complaints");
  });

  server.on("error", (error) => {
    console.error("Server error:", error.message);
  });
}

startServer().catch((error) => {
  console.error("Failed to start CivicSense:", error);
  process.exitCode = 1;
});
