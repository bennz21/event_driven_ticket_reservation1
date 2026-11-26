-- MySQL InnoDB Schema for Event & Ticket Booking Platform
-- Note: Admin credentials are stored ONLY in .env, not in the database.

CREATE TABLE IF NOT EXISTS users (
    id INT NOT NULL AUTO_INCREMENT,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('organizer', 'public') NOT NULL,
    status ENUM('active', 'blocked') NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_email (email),
    KEY ix_users_role (role),
    KEY ix_users_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS events (
    id INT NOT NULL AUTO_INCREMENT,
    organizer_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    event_date DATE NOT NULL,
    event_time TIME NOT NULL,
    venue VARCHAR(200) NOT NULL,
    ticket_price DECIMAL(10, 2) NOT NULL,
    seating_type ENUM('seated', 'open') NOT NULL DEFAULT 'open',
    total_rows INT NULL,
    seats_per_row INT NULL,
    total_tickets INT NOT NULL,
    available_tickets INT NOT NULL,
    approval_status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_events_organizer_id (organizer_id),
    KEY ix_events_title (title),
    KEY ix_events_event_date (event_date),
    KEY ix_events_venue (venue),
    KEY ix_events_seating_type (seating_type),
    KEY ix_events_approval_status (approval_status),
    KEY ix_events_approval_date (approval_status, event_date),
    CONSTRAINT fk_events_organizer FOREIGN KEY (organizer_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bookings (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    event_id INT NOT NULL,
    ticket_count INT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status ENUM('pending', 'confirmed', 'cancelled', 'failed') NOT NULL DEFAULT 'pending',
    booked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY ix_bookings_user_id (user_id),
    KEY ix_bookings_event_id (event_id),
    KEY ix_bookings_status (status),
    KEY ix_bookings_booked_at (booked_at),
    KEY ix_bookings_user_status (user_id, status),
    CONSTRAINT fk_bookings_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_bookings_event FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS seats (
    id INT NOT NULL AUTO_INCREMENT,
    event_id INT NOT NULL,
    row_label VARCHAR(10) NOT NULL,
    seat_number INT NOT NULL,
    status ENUM('available', 'pending', 'booked') NOT NULL DEFAULT 'available',
    booking_id INT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_seat_event_row_num (event_id, row_label, seat_number),
    KEY ix_seats_event_id (event_id),
    KEY ix_seats_status (status),
    KEY ix_seats_booking_id (booking_id),
    CONSTRAINT fk_seats_event FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
    CONSTRAINT fk_seats_booking FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payments (
    id INT NOT NULL AUTO_INCREMENT,
    booking_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status ENUM('pending', 'success', 'failed', 'refunded') NOT NULL DEFAULT 'pending',
    gateway_transaction_id VARCHAR(120) NULL,
    paid_at DATETIME NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_payments_booking_id (booking_id),
    KEY ix_payments_status (status),
    KEY ix_payments_gateway_txn (gateway_transaction_id),
    CONSTRAINT fk_payments_booking FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tickets (
    id INT NOT NULL AUTO_INCREMENT,
    booking_id INT NOT NULL,
    event_id INT NOT NULL,
    seat_id INT NULL,
    seat_label VARCHAR(20) NULL,
    ticket_code VARCHAR(64) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tickets_ticket_code (ticket_code),
    KEY ix_tickets_booking_id (booking_id),
    KEY ix_tickets_event_id (event_id),
    CONSTRAINT fk_tickets_booking FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE CASCADE,
    CONSTRAINT fk_tickets_event FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
    CONSTRAINT fk_tickets_seat FOREIGN KEY (seat_id) REFERENCES seats (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
