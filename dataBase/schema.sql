DROP TABLE IF EXISTS story;
DROP TABLE IF EXISTS story_question;
DROP TABLE IF EXISTS story_category;
DROP TABLE IF EXISTS voice;
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS dialogue;
DROP TABLE IF EXISTS user_answer;
DROP TABLE IF EXISTS user_answer;
DROP TABLE IF EXISTS favorite;


-- 故事表
CREATE TABLE story
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER   NOT NULL,
    title       TEXT      NOT NULL,
    content     TEXT      NOT NULL,
    author      VARCHAR(255),
    length      INTEGER   NOT NULL,
    created     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES story_category (id)
);

-- 故事对应的问题表（待定）
CREATE TABLE story_question
(
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id INTEGER,
    content  TEXT,
    created  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES story (id)
);

-- 故事分类表
CREATE TABLE story_category
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    created     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 声音表
CREATE TABLE voice
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER      NOT NULL,
    voice_desc VARCHAR(255) NOT NULL,
    created    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id)
);

-- 故事及mp3目录对应表
CREATE TABLE story_audio
(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    story_id   INTEGER   NOT NULL,
    voice_id   INTEGER   NOT NULL,
    audio_path TEXT      NOT NULL,
    created    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_id) REFERENCES story (id),
    FOREIGN KEY (voice_id) REFERENCES voice (id)
);

-- 用户表
CREATE TABLE user
(
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     VARCHAR(255)         NOT NULL,
    password INTEGER VARCHAR(255) NOT NULL,
    sex      INT(2),
    phone    INTEGER,
    email    VARCHAR(255),
    created  TIMESTAMP            NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 对话表
CREATE TABLE dialogue
(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER   NOT NULL,
    role    INT(2),
    content TEXT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id)
);

-- 用户回答表
CREATE TABLE user_answer
(
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    story_question_id INTEGER   NOT NULL,
    dialogue_id       INTEGER   NOT NULL,
    score             INTEGER   NOT NULL,
    created           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (story_question_id) REFERENCES story_question (id),
    FOREIGN KEY (dialogue_id) REFERENCES dialogue (id)
);

-- 收藏表
CREATE TABLE favorite
(
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id  INTEGER   NOT NULL,
    story_id INTEGER   NOT NULL,
    created  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (story_id) REFERENCES story (id)
);

