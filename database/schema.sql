CREATE TABLE IF NOT EXISTS `blacklist` (
  `user_id` varchar(20) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `messages` (
  `message_id` varchar(20) NOT NULL,
  `ability_name` varchar(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS `votes` (
  `user_id` varchar(255) NOT NULL,
  `ability_name` varchar(255) NOT NULL,
  `value` int(2) NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS `warns` (
  `id` int(11) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);