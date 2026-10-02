-- 001_initial_data.sql
-- 初始测试数据，覆盖用户、校区、建筑、设施、课程、排课、活动和行为记录。
-- 数据使用显式主键并配合 ON CONFLICT，方便重复导入验证。

BEGIN;

INSERT INTO users (user_id, name, department) VALUES
  (1, '张明', '信息科学与工程学院'),
  (2, '李芳', '计算机科学技术学院'),
  (3, '王强', '新闻学院'),
  (4, '陈晨', '计算机科学技术学院'),
  (5, '赵敏', '新闻学院'),
  (6, '刘洋', '数学科学学院'),
  (7, '周宁', '基础医学院'),
  (8, '孙洁', '体育教学部')
ON CONFLICT (user_id) DO UPDATE SET
  name = EXCLUDED.name,
  department = EXCLUDED.department;

INSERT INTO teacher (user_id, title) VALUES
  (1, '教授'),
  (2, '副教授'),
  (3, '讲师'),
  (8, '讲师')
ON CONFLICT (user_id) DO UPDATE SET
  title = EXCLUDED.title;

INSERT INTO student (user_id, major) VALUES
  (4, '计算机科学与技术'),
  (5, '新闻学'),
  (6, '数据科学与大数据技术'),
  (7, '临床医学')
ON CONFLICT (user_id) DO UPDATE SET
  major = EXCLUDED.major;

INSERT INTO campus (campus_id, name, address) VALUES
  (1, '邯郸校区', '上海市杨浦区邯郸路220号'),
  (2, '江湾校区', '上海市杨浦区淞沪路2005号'),
  (3, '枫林校区', '上海市徐汇区医学院路138号'),
  (4, '张江校区', '上海市浦东新区张衡路825号')
ON CONFLICT (campus_id) DO UPDATE SET
  name = EXCLUDED.name,
  address = EXCLUDED.address;

INSERT INTO building (building_id, name, type, campus_id) VALUES
  (1, '光华楼', '综合楼', 1),
  (2, '第二教学楼', '教学楼', 1),
  (3, '文科图书馆', '图书馆', 1),
  (4, '江湾体育馆', '体育场馆', 2),
  (5, '枫林图书馆', '图书馆', 3),
  (6, '张江实验楼', '实验楼', 4),
  (7, '本部食堂', '食堂', 1)
ON CONFLICT (building_id) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  campus_id = EXCLUDED.campus_id;

INSERT INTO facility (facility_id, name, type, open_time, building_id) VALUES
  (1, '光华楼东辅楼102', '教室', '每日 08:00-22:00', 1),
  (2, '光华楼报告厅', '报告厅', '工作日 09:00-21:00', 1),
  (3, 'H2201', '教室', '每日 07:30-22:30', 2),
  (4, 'H2303自习室', '自习室', '每日 08:00-23:00', 2),
  (5, '文科图书馆阅览室', '图书阅览室', '周一至周日 08:00-22:00', 3),
  (6, '江湾篮球馆', '体育设施', '周一至周日 09:00-21:00', 4),
  (7, '枫林医学阅览室', '图书阅览室', '每日 08:00-22:00', 5),
  (8, '张江AI实验室', '实验室', '工作日 09:00-18:00', 6),
  (9, '本部食堂一楼', '餐饮服务', '每日 06:30-20:00', 7)
ON CONFLICT (facility_id) DO UPDATE SET
  name = EXCLUDED.name,
  type = EXCLUDED.type,
  open_time = EXCLUDED.open_time,
  building_id = EXCLUDED.building_id;

INSERT INTO course (course_master_code, name) VALUES
  ('COMP130015', '数据库系统原理'),
  ('COMP130136', '人工智能导论'),
  ('MATH120011', '高等数学A'),
  ('JOUR110001', '新闻传播导论'),
  ('MEDI200101', '医学统计学'),
  ('PE101', '篮球')
ON CONFLICT (course_master_code) DO UPDATE SET
  name = EXCLUDED.name;

INSERT INTO course_section (course_code, course_master_code) VALUES
  ('COMP130015.01', 'COMP130015'),
  ('COMP130015.02', 'COMP130015'),
  ('COMP130136.01', 'COMP130136'),
  ('MATH120011.01', 'MATH120011'),
  ('JOUR110001.01', 'JOUR110001'),
  ('MEDI200101.01', 'MEDI200101'),
  ('PE101.01', 'PE101')
ON CONFLICT (course_code) DO UPDATE SET
  course_master_code = EXCLUDED.course_master_code;

INSERT INTO course_offering (offering_id, course_code, semester) VALUES
  (1, 'COMP130015.01', '2025-2026 春季学期'),
  (2, 'COMP130015.02', '2025-2026 春季学期'),
  (3, 'COMP130136.01', '2025-2026 春季学期'),
  (4, 'MATH120011.01', '2025-2026 春季学期'),
  (5, 'JOUR110001.01', '2025-2026 春季学期'),
  (6, 'MEDI200101.01', '2025-2026 春季学期'),
  (7, 'PE101.01', '2025-2026 春季学期')
ON CONFLICT (offering_id) DO UPDATE SET
  course_code = EXCLUDED.course_code,
  semester = EXCLUDED.semester;

INSERT INTO course_offering_teacher (offering_id, teacher_id) VALUES
  (1, 2),
  (2, 1),
  (3, 2),
  (4, 1),
  (5, 3),
  (6, 1),
  (7, 8)
ON CONFLICT (offering_id, teacher_id) DO NOTHING;

INSERT INTO course_offering_schedule
  (offering_id, day_of_week, start_period, end_period, week_type, facility_id)
VALUES
  (1, '周一', 3, 4, '每周', 3),
  (1, '周三', 3, 4, '双周', 8),
  (2, '周二', 5, 6, '每周', 1),
  (3, '周四', 7, 8, '每周', 8),
  (4, '周一', 1, 2, '每周', 3),
  (4, '周三', 1, 2, '每周', 3),
  (5, '周二', 3, 4, '每周', 5),
  (6, '周五', 3, 4, '每周', 7),
  (7, '周五', 7, 8, '每周', 6)
ON CONFLICT (offering_id, day_of_week, start_period, end_period, week_type) DO UPDATE SET
  facility_id = EXCLUDED.facility_id;

INSERT INTO activity
  (activity_id, name, description, start_time, end_time, organizer, facility_id)
VALUES
  (1, '新生数据库实践讲座', '介绍校园问答系统背后的数据库建模、约束设计和查询优化方法。', '2026-05-20 14:00:00', '2026-05-20 16:00:00', '计算机科学技术学院', 2),
  (2, '校园开放日导览', '面向访客和新生的邯郸校区建筑与学习空间导览。', '2026-05-18 09:00:00', '2026-05-18 11:00:00', '招生办公室', 1),
  (3, '江湾篮球友谊赛', '校内篮球社团在江湾体育馆组织的交流赛。', '2026-05-24 18:00:00', '2026-05-24 20:00:00', '体育教学部', 6),
  (4, '图书馆信息素养工作坊', '讲解文献检索、数据库资源使用和论文资料管理。', '2026-05-21 19:00:00', '2026-05-21 20:30:00', '图书馆', 5),
  (5, '张江AI实验室参观', '参观张江AI实验室，了解智能系统原型和实验平台。', '2026-05-23 10:00:00', '2026-05-23 11:30:00', '张江研究院', 8)
ON CONFLICT (activity_id) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  start_time = EXCLUDED.start_time,
  end_time = EXCLUDED.end_time,
  organizer = EXCLUDED.organizer,
  facility_id = EXCLUDED.facility_id;

INSERT INTO user_activity (user_id, activity_id, status) VALUES
  (4, 1, '待参加'),
  (5, 1, '待参加'),
  (6, 1, '已签到'),
  (4, 2, '已完成'),
  (5, 2, '已完成'),
  (6, 3, '待参加'),
  (7, 4, '待参加'),
  (4, 5, '待参加')
ON CONFLICT (user_id, activity_id) DO UPDATE SET
  status = EXCLUDED.status;

INSERT INTO query_log (log_id, user_id, query_category, query_content, query_time) VALUES
  (1, 4, '建筑', '邯郸校区有哪些教学楼', '2026-05-10 09:10:00'),
  (2, 4, '设施', '第二教学楼哪里可以自习', '2026-05-10 09:12:00'),
  (3, 5, '课程', '数据库系统原理周几上课', '2026-05-10 10:20:00'),
  (4, 6, '教师', '李芳老师这学期教什么课', '2026-05-10 11:05:00'),
  (5, 7, '活动', '近期有哪些校园活动', '2026-05-10 13:30:00'),
  (6, 5, '统计', '统计每个校区建筑数量', '2026-05-10 14:00:00'),
  (7, 4, '活动', '数据库实践讲座在哪里', '2026-05-10 15:18:00'),
  (8, 6, '设施', '江湾篮球馆开放时间', '2026-05-10 16:40:00'),
  (9, 7, '课程', '医学统计学上课地点', '2026-05-10 17:00:00'),
  (10, 4, '用户', '查看我的账户信息', '2026-05-10 18:15:00')
ON CONFLICT (log_id) DO UPDATE SET
  user_id = EXCLUDED.user_id,
  query_category = EXCLUDED.query_category,
  query_content = EXCLUDED.query_content,
  query_time = EXCLUDED.query_time;

SELECT setval(pg_get_serial_sequence('users', 'user_id'), (SELECT max(user_id) FROM users), true);
SELECT setval(pg_get_serial_sequence('campus', 'campus_id'), (SELECT max(campus_id) FROM campus), true);
SELECT setval(pg_get_serial_sequence('building', 'building_id'), (SELECT max(building_id) FROM building), true);
SELECT setval(pg_get_serial_sequence('facility', 'facility_id'), (SELECT max(facility_id) FROM facility), true);
SELECT setval(pg_get_serial_sequence('course_offering', 'offering_id'), (SELECT max(offering_id) FROM course_offering), true);
SELECT setval(pg_get_serial_sequence('activity', 'activity_id'), (SELECT max(activity_id) FROM activity), true);
SELECT setval(pg_get_serial_sequence('query_log', 'log_id'), (SELECT max(log_id) FROM query_log), true);

COMMIT;
