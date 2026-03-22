/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19-11.8.3-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: napsterlegal_analytics
-- ------------------------------------------------------
-- Server version	11.8.3-MariaDB-0+deb13u1 from Debian

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Table structure for table `analytics_artiststats`
--

DROP TABLE IF EXISTS `analytics_artiststats`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `analytics_artiststats` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `artist_id` uuid NOT NULL,
  `date` date NOT NULL,
  `total_plays` int(10) unsigned NOT NULL CHECK (`total_plays` >= 0),
  `unique_listeners` int(10) unsigned NOT NULL CHECK (`unique_listeners` >= 0),
  `new_followers` int(10) unsigned NOT NULL CHECK (`new_followers` >= 0),
  `top_track_id` uuid DEFAULT NULL,
  `revenue_estimate` decimal(10,2) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `analytics_artiststats_artist_id_date_d845845f_uniq` (`artist_id`,`date`),
  KEY `analytics_artiststats_artist_id_124e1c77` (`artist_id`),
  KEY `analytics_artiststats_date_21a00cac` (`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `analytics_artiststats`
--

LOCK TABLES `analytics_artiststats` WRITE;
/*!40000 ALTER TABLE `analytics_artiststats` DISABLE KEYS */;
set autocommit=0;
/*!40000 ALTER TABLE `analytics_artiststats` ENABLE KEYS */;
UNLOCK TABLES;
commit;

--
-- Table structure for table `analytics_playevent`
--

DROP TABLE IF EXISTS `analytics_playevent`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `analytics_playevent` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `track_id` uuid NOT NULL,
  `user_id` uuid DEFAULT NULL,
  `session_id` varchar(100) NOT NULL,
  `listened_duration` int(10) unsigned NOT NULL CHECK (`listened_duration` >= 0),
  `completed` tinyint(1) NOT NULL,
  `ip_address` char(39) DEFAULT NULL,
  `country_code` varchar(2) NOT NULL,
  `device_type` varchar(50) NOT NULL,
  `timestamp` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `analytics_playevent_timestamp_66e17013` (`timestamp`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `analytics_playevent`
--

LOCK TABLES `analytics_playevent` WRITE;
/*!40000 ALTER TABLE `analytics_playevent` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `analytics_playevent` VALUES
(1,'48c49d6b-223d-4ce8-9c8f-a3a03b40f8a8','09d0cae5-4a74-4448-bf3a-566635d01fa1','l0kfcmwx7mil6houaz0yn0sp4l8o7afl',0,0,'127.0.0.1','','desktop','2026-03-22 09:02:23.048395');
/*!40000 ALTER TABLE `analytics_playevent` ENABLE KEYS */;
UNLOCK TABLES;
commit;

--
-- Table structure for table `analytics_searchlog`
--

DROP TABLE IF EXISTS `analytics_searchlog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `analytics_searchlog` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `query` varchar(200) NOT NULL,
  `user_id` uuid DEFAULT NULL,
  `results_count` int(10) unsigned NOT NULL CHECK (`results_count` >= 0),
  `clicked_track_id` uuid DEFAULT NULL,
  `timestamp` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `analytics_searchlog_timestamp_55d0145a` (`timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `analytics_searchlog`
--

LOCK TABLES `analytics_searchlog` WRITE;
/*!40000 ALTER TABLE `analytics_searchlog` DISABLE KEYS */;
set autocommit=0;
/*!40000 ALTER TABLE `analytics_searchlog` ENABLE KEYS */;
UNLOCK TABLES;
commit;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `django_migrations` VALUES
(1,'contenttypes','0001_initial','2026-03-22 04:19:15.362609'),
(2,'contenttypes','0002_remove_content_type_name','2026-03-22 04:19:15.439772'),
(3,'auth','0001_initial','2026-03-22 04:19:15.511794'),
(4,'auth','0002_alter_permission_name_max_length','2026-03-22 04:19:15.636764'),
(5,'auth','0003_alter_user_email_max_length','2026-03-22 04:19:15.694982'),
(6,'auth','0004_alter_user_username_opts','2026-03-22 04:19:15.754927'),
(7,'auth','0005_alter_user_last_login_null','2026-03-22 04:19:15.809332'),
(8,'auth','0006_require_contenttypes_0002','2026-03-22 04:19:15.856166'),
(9,'auth','0007_alter_validators_add_error_messages','2026-03-22 04:19:15.925894'),
(10,'auth','0008_alter_user_username_max_length','2026-03-22 04:19:15.993195'),
(11,'auth','0009_alter_user_last_name_max_length','2026-03-22 04:19:16.052190'),
(12,'auth','0010_alter_group_name_max_length','2026-03-22 04:19:16.177878'),
(13,'auth','0011_update_proxy_permissions','2026-03-22 04:19:16.222971'),
(14,'auth','0012_alter_user_first_name_max_length','2026-03-22 04:19:16.282410'),
(15,'accounts','0001_initial','2026-03-22 04:19:16.386457'),
(16,'admin','0001_initial','2026-03-22 04:19:16.573675'),
(17,'admin','0002_logentry_remove_auto_add','2026-03-22 04:19:16.639687'),
(18,'admin','0003_logentry_add_action_flag_choices','2026-03-22 04:19:16.708132'),
(19,'sessions','0001_initial','2026-03-22 04:19:16.764269'),
(20,'analytics','0001_initial','2026-03-22 04:42:06.507644');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;
commit;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed on 2026-03-22 10:35:05
