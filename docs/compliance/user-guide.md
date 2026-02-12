# Compliance System User Guide

This guide provides step-by-step instructions for using the Jackdaw Sentry compliance system.

## 🎯 Getting Started

### Prerequisites
- Access to the compliance dashboard
- Valid user credentials with compliance permissions
- Understanding of basic compliance concepts

### First Login
1. Navigate to the compliance dashboard: `https://compliance.jackdawsentry.com`
2. Enter your credentials
3. Complete two-factor authentication (if enabled)
4. Review the welcome message and system overview

## 📊 Dashboard Overview

### Main Dashboard Components

#### Statistics Cards
- **SAR Reports**: Total Suspicious Activity Reports filed
- **Risk Assessments**: Number of risk assessments completed
- **Open Cases**: Active compliance cases
- **Pending Deadlines**: Upcoming regulatory deadlines

#### Charts and Visualizations
- **Compliance Trend**: 30-day compliance score trend
- **Report Distribution**: Breakdown by report type
- **Risk Assessment Levels**: Distribution of risk levels
- **Case Management**: Open vs closed cases over time

#### Quick Actions
- **Create Case**: Start a new compliance case
- **Generate Report**: Create regulatory report
- **Risk Assessment**: Run risk assessment on entity
- **View Deadlines**: Check upcoming deadlines

## 📋 Case Management

### Creating a New Case

#### Manual Case Creation
1. Click **"Create Case"** in the dashboard
2. Fill in case details:
   - **Title**: Descriptive case title
   - **Description**: Detailed case description
   - **Case Type**: Select from dropdown (suspicious_activity, sanctions_screening, etc.)
   - **Priority**: Low, Medium, High, or Critical
   - **Assigned To**: Select investigator
3. Click **"Create Case"** to save

#### Automatic Case Creation
Cases can be automatically created when:
- Risk assessment exceeds threshold
- Suspicious transaction pattern detected
- Sanctions list match found
- External alert received

### Managing Cases

#### Case Status Updates
1. Navigate to **Cases** tab
2. Click on case to view details
3. Use status dropdown to update:
   - **Open**: Case is being investigated
   - **In Progress**: Active investigation underway
   - **Under Review**: Review phase
   - **Escalated**: Escalated to senior staff
   - **Closed**: Investigation completed
   - **Archived**: Case archived for reference

#### Adding Evidence
1. Open case details
2. Click **"Add Evidence"**
3. Select evidence type:
   - **Transaction Data**: Blockchain transaction details
   - **Address Analysis**: Address risk analysis
   - **External Reports**: Third-party reports
   - **Documents**: PDF, images, or other files
4. Upload or enter evidence details
5. Click **"Add Evidence"**

#### Case Collaboration
- **Comments**: Add comments for team collaboration
- **Assignments**: Reassign case to different investigator
- **Tags**: Add tags for categorization
- **Notes**: Add investigation notes

## 📈 Risk Assessment

### Running Risk Assessment

#### Address Risk Assessment
1. Navigate to **Risk Assessment** tab
2. Enter blockchain address or transaction hash
3. Select entity type (address, transaction, wallet)
4. Choose trigger type (automatic, manual, threshold_breach)
5. Click **"Run Assessment"**

#### Understanding Risk Scores
- **Low (0-0.3)**: Minimal risk, standard monitoring
- **Medium (0.3-0.6)**: Moderate risk, enhanced monitoring
- **High (0.6-0.8)**: High risk, investigation recommended
- **Critical (0.8-0.9)**: Critical risk, immediate action required
- **Severe (0.9-1.0)**: Severe risk, emergency response

### Risk Factors
Risk assessments consider multiple factors:
- **Transaction Volume**: Unusual transaction amounts
- **Address Risk**: Known high-risk addresses
- **Amount Anomaly**: Irregular transaction patterns
- **Geographic Risk**: High-risk jurisdictions
- **Counterparty Risk**: Risk associated with transaction partners

### Risk Recommendations
Based on assessment results:
- **Low Risk**: Continue standard monitoring
- **Medium Risk**: Enhanced monitoring, periodic review
- **High Risk**: Investigate further, consider reporting
- **Critical**: Immediate investigation, likely reporting required
- **Severe**: Emergency response, immediate reporting

## 📑 Regulatory Reporting

### Creating SAR Reports

#### SAR Report Creation
1. Navigate to **Regulatory Reports** tab
2. Click **"Create SAR Report"**
3. Select jurisdiction (USA_FinCEN, UK_FCA, EU)
4. Enter entity details:
   - **Entity ID**: Address or transaction hash
   - **Entity Type**: Address, transaction, or wallet
5. Fill suspicious activity details:
   - **Description**: Detailed activity description
   - **Amount**: Transaction amounts
   - **Transaction Details**: Additional transaction information
6. Click **"Create Report"**

#### Report Types
- **SAR**: Suspicious Activity Report
- **CTR**: Currency Transaction Report
- **STR**: Suspicious Transaction Report
- **Custom**: Custom regulatory reports

### Deadline Management

#### Viewing Deadlines
1. Navigate to **Deadlines** tab
2. View upcoming deadlines sorted by urgency:
   - **Red**: Due within 24 hours
   - **Orange**: Due within 3 days
   - **Yellow**: Due within 7 days
   - **Green**: Due after 7 days

#### Deadline Actions
- **Handle**: Take action on deadline
- **Snooze**: Temporarily postpone (with justification)
- **Escalate**: Escalate to management
- **Complete**: Mark deadline as completed

### Report Submission

#### Submission Process
1. Review report details for accuracy
2. Ensure all required fields are completed
3. Click **"Submit Report"**
4. Receive confirmation with submission ID
5. Track submission status in dashboard

#### Submission Status
- **Draft**: Report being prepared
- **Submitted**: Report submitted to regulator
- **Acknowledged**: Regulator acknowledged receipt
- **Rejected**: Report rejected (requires resubmission)
- **Completed**: Report processing completed

## 🔍 Audit Trail

### Viewing Audit Events

#### Audit Event Types
- **User Actions**: Login, case creation, status updates
- **System Events**: Automated processes, system changes
- **Compliance Events**: Regulatory actions, deadline events
- **Security Events**: Authentication, authorization events

#### Filtering Events
1. Navigate to **Audit Trail** tab
2. Use filters to narrow results:
   - **Date Range**: Select time period
   - **Event Type**: Filter by event category
   - **User ID**: Filter by specific user
   - **Resource Type**: Filter by resource type
3. Click **"Apply Filters"**

### Audit Reports

#### Generating Audit Reports
1. Navigate to **Audit Trail** tab
2. Click **"Generate Report"**
3. Select report parameters:
   - **Date Range**: Report period
   - **Event Types**: Include specific event types
   - **Format**: PDF, CSV, or JSON
4. Click **"Generate Report"**
5. Download generated report

#### Audit Integrity
- **Hash Chaining**: Cryptographic verification of audit log integrity
- **Immutable Records**: Tamper-evident audit trail
- **Verification Reports**: Periodic integrity verification

## ⚙️ System Configuration

### User Settings

#### Profile Management
1. Click user profile in top-right corner
2. Update personal information:
   - **Name**: Display name
   - **Email**: Contact email
   - **Phone**: Phone number (optional)
3. Change password if needed
4. Click **"Save Changes"**

#### Notification Preferences
1. Navigate to **Settings** → **Notifications**
2. Configure notification preferences:
   - **Email Notifications**: Enable/disable email alerts
   - **Deadline Alerts**: Configure deadline reminders
   - **Case Updates**: Receive case status changes
   - **System Alerts**: System maintenance notifications
3. Click **"Save Preferences"**

### System Preferences

#### Dashboard Configuration
1. Navigate to **Settings** → **Dashboard**
2. Customize dashboard:
   - **Layout**: Arrange dashboard components
   - **Time Ranges**: Set default time ranges for charts
   - **Refresh Rate**: Configure auto-refresh interval
   - **Default Views**: Set default dashboard views

#### Risk Thresholds
1. Navigate to **Settings** → **Risk Thresholds**
2. Configure risk assessment thresholds:
   - **Auto-Escalation**: Enable automatic escalation
   - **Threshold Values**: Set risk score thresholds
   - **Notification Levels**: Configure alert levels
3. Click **"Save Settings**

## 📱 Mobile Access

### Mobile Dashboard
- Access compliance dashboard on mobile devices
- Responsive design for tablets and smartphones
- Touch-optimized interface
- Offline mode for basic functions

### Mobile Notifications
- Push notifications for urgent alerts
- SMS notifications for critical deadlines
- Email notifications for non-urgent updates

## 🔍 Search and Filtering

### Advanced Search

#### Global Search
1. Use search bar in top navigation
2. Enter search terms:
   - **Case IDs**: Search by case identifier
   - **Addresses**: Blockchain addresses
   - **Transaction Hashes**: Transaction identifiers
   - **User Names**: Investigator names
3. Press Enter or click search icon

#### Search Filters
- **Date Range**: Filter by creation date
- **Status**: Filter by case status
- **Priority**: Filter by priority level
- **Assigned To**: Filter by investigator
- **Tags**: Filter by case tags

### Saved Searches
1. Perform search with desired filters
2. Click **"Save Search"**
3. Enter search name
4. Click **"Save"**
5. Access saved searches from dropdown

## 📊 Reports and Analytics

### Standard Reports

#### Case Statistics
- Total cases created
- Cases by status
- Cases by priority
- Cases by investigator
- Average case resolution time

#### Risk Assessment Analytics
- Risk level distribution
- Risk factor analysis
- Assessment trends over time
- High-risk entity identification

#### Regulatory Reporting Metrics
- Reports by jurisdiction
- Submission success rates
- Deadline compliance
- Report processing times

### Custom Reports
1. Navigate to **Reports** tab
2. Click **"Create Custom Report"**
3. Select data sources and metrics
4. Configure report parameters
5. Choose output format
6. Click **"Generate Report"**

## 🚨 Alerts and Notifications

### Alert Types
- **Risk Alerts**: High-risk assessments
- **Deadline Alerts**: Upcoming regulatory deadlines
- **System Alerts**: System issues or maintenance
- **Security Alerts**: Security events or breaches

### Managing Alerts
1. Navigate to **Alerts** tab
2. View active alerts
3. Take appropriate action:
   - **Acknowledge**: Acknowledge alert receipt
   - **Resolve**: Mark alert as resolved
   - **Escalate**: Escalate to management
   - **Snooze**: Temporarily dismiss alert

### Notification Channels
- **In-App**: Dashboard notifications
- **Email**: Email alerts and summaries
- **SMS**: Critical alerts via text message
- **Webhook**: Integration with external systems

## 🔐 Security Best Practices

### Account Security
- Use strong, unique passwords
- Enable two-factor authentication
- Regular password updates
- Secure session management

### Data Protection
- Log out when finished
- Don't share credentials
- Report suspicious activity
- Use secure networks

### Compliance Security
- Follow data handling procedures
- Maintain confidentiality
- Report compliance violations
- Attend security training

## 📞 Getting Help

### Help Resources
- **User Manual**: This documentation
- **Video Tutorials**: Step-by-step video guides
- **FAQ**: Frequently asked questions
- **Support Portal**: Submit support requests

### Contact Support
- **Email**: compliance-support@jackdawsentry.com
- **Phone**: +1-555-COMPLY (during business hours)
- **Chat**: In-app chat support
- **Tickets**: Support ticket system

### Training Resources
- **Online Training**: Self-paced training modules
- **Workshops**: Live training sessions
- **Webinars**: Regular educational webinars
- **Documentation**: Comprehensive documentation library

## 📋 Quick Reference

### Common Tasks
- **Create Case**: Cases → Create Case → Fill form → Save
- **Run Risk Assessment**: Risk Assessment → Enter address → Run Assessment
- **Submit SAR**: Reports → Create SAR → Fill form → Submit
- **Check Deadlines**: Deadlines → View upcoming → Handle as needed
- **View Audit Trail**: Audit Trail → Filter events → Export if needed

### Keyboard Shortcuts
- **Ctrl+N**: Create new case
- **Ctrl+F**: Search
- **Ctrl+R**: Refresh dashboard
- **Ctrl+S**: Save current work
- **Esc**: Cancel current operation

### Important URLs
- **Dashboard**: `/compliance/`
- **Cases**: `/compliance/cases`
- **Risk Assessment**: `/compliance/risk`
- **Reports**: `/compliance/reports`
- **Audit Trail**: `/compliance/audit`
- **Settings**: `/compliance/settings`

---

**Last Updated**: 2024-01-15
**Version**: 1.5.0
**For Support**: compliance@jackdawsentry.com
