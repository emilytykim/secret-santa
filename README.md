images/tree_group1.png

### Overview

A full-stack web application to automate Secret Santa events, from participant registration to anonymous messaging and email notifications. Built to streamline the traditional manual process and enhance participant interaction.

### Motivation

Manual Secret Santa processes often lead to confusion in participant matching and communication. I wanted to create an end-to-end automated solution that handles registration, matching, anonymous communication, and automated notifications.

More personally, as an international student studying abroad, I wanted to celebrate Secret Santa with my friends back home. But since everyone was swamped and didn't have time to meet in person and draw names, I thought — why not leverage computer science to solve this?

While organizing Secret Santa, I also noticed my friends often struggled with choosing the right gift — "What color do they like?", "Would they enjoy this?". So, I built the anonymous messaging system to let participants ask their recipient up to 3 fun, mystery questions before selecting a gift!

### Features

🔐 Secure Login Flow: Each participant securely logs in to view their assigned match

🧩 Automated Participant Matching: Once all participants are registered, the system randomly assigns Secret Santas

📩 Automated Email Notifications:

Party invitations automatically sent to all participants upon registration completion

Matching result notifications sent after random assignment

💬 Anonymous Messaging System: Participants can send up to 3 anonymous questions to their assigned recipient before selecting a gift

📥 Inbox System: Participants can view messages and replies from their assigned recipient

🗂️ Data Persistence: All participant data, matching results, and messages are stored in an SQLite database

🌐 AJAX-Powered Dynamic UI: Real-time message sending and updates without page reloads


### Tech Stack

Backend: Python (Flask), SQLite

Frontend: HTML, CSS, JavaScript (AJAX)

Email Service: SMTP (Gmail)

Database: SQLite, Supabase


### How it works

1. Admin creates a party

2. Participants register with name and email

3. System sends party invitation emails via SMTP

4. After all participants are registered, the system assigns matches and notifies participants via email

5. Participants log in to view their assigned match

6. Participants send up to 3 anonymous messages to their match

7. Participants check their inbox to view received messages and responses

