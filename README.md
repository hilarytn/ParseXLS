
## Application Features and Line Visualization Page Guide

### Introduction
The application is designed to handle Excel file uploads, process the data, and provide visualizations for better understanding. This guide provides an overview of the application's features and functionalities, including a detailed description of the Line Visualization page.

### Application Features

#### Excel File Handling
- Users can upload Excel files containing production data.
- The application processes the uploaded files and updates the master file and line-specific files accordingly.
- Data cleanup functionality is available to remove uploaded files after processing.

#### User Authentication
- Users can register for an account or log in using their credentials.
- Authentication ensures that only authorized users can access the application's functionalities.

#### Data Visualization
- The application provides visualizations to help users analyze production line data effectively.

### Line Visualization Page

#### Line Information
- Upon accessing the Line Visualization page, users are greeted with information about the specific production line, identified by its number.

#### Download and Navigation
- Users can download data related to the current production line by clicking the "Download Line {{ line_number }}" button.
- The "Go Back" button redirects users to the Home page.
- The "Go To Visualization" button navigates users to the visualization section on the page.

#### Data Table
- The data table displays detailed information about each entry related to the production line, including:
  - Line number
  - Date
  - Description
  - Start time
  - End time
  - Time gap
  - Downtime

#### Visualization
- **Pie Chart**: Presents the distribution of product percentages based on the data associated with the production line.
- **Bar Chart**: Illustrates the aggregated time gap and downtime for each product.
- **Bar Chart (Tgaps and Count)**: Visualizes the time gaps and counts for each product.

#### Instructions
1. **Download Line Data**:
   - Click the "Download Line {{ line_number }}" button to download data related to the current production line.

2. **Navigation**:
   - Use the "Go Back" button to return to the Home page.
   - Click the "Go To Visualization" button to quickly navigate to the visualization section.

3. **Data Table**:
   - Review the detailed information provided in the data table.

4. **Visualization**:
   - Interpret the pie chart, bar chart, and tgaps/count chart to gain insights into the production line's performance.
