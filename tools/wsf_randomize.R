# =============================================================================
#  wsf_randomize.R — การสุ่มลำดับรุ่นสำหรับ WSF Sandbox
#  เผยแพร่ล่วงหน้าเพื่อให้ตรวจสอบได้  ·  ห้ามแก้ไขหลังประกาศ seed
# =============================================================================

library(dplyr)

# ---- 1) ตั้งค่า --------------------------------------------------------------
SEED    <- 25690801L      # ประกาศต่อหน้าพยานในวันจับสลาก
N_WAVE  <- 4L             # จำนวนรุ่น
set.seed(SEED)

# ---- 2) โหลดข้อมูลและสร้างชั้น -----------------------------------------------
schools <- read.csv("sandbox_frame.csv", fileEncoding = "UTF-8") %>%
  mutate(
    size_band = cut(students, breaks = c(0, 60, 120, Inf),
                    labels = c("เล็กมาก", "เล็ก", "กลาง"), right = TRUE),
    pov_band  = ntile(poverty_rate, 3),
    short_staff = ifelse(teachers < classrooms, "ขาดครู", "ครูครบ"),
    stratum   = paste(region, size_band, pov_band, short_staff, sep = "|")
  )

# ---- 3) ยุบชั้นที่มีสมาชิกน้อยเกินไป (กฎประกาศล่วงหน้า) ------------------------
small <- schools %>% count(stratum) %>% filter(n < N_WAVE) %>% pull(stratum)
schools <- schools %>%
  mutate(stratum = ifelse(stratum %in% small,
                          paste(region, size_band, sep = "|"), stratum))

# ---- 4) สุ่มลำดับรุ่นภายในแต่ละชั้น -------------------------------------------
assign_waves <- function(df) {
  n <- nrow(df)
  waves <- rep(1:N_WAVE, length.out = n)          # กระจายเท่า ๆ กัน
  df$wave <- sample(waves, size = n, replace = FALSE)
  df
}
assigned <- schools %>% group_split(stratum) %>%
  lapply(assign_waves) %>% bind_rows()

# ---- 5) ตรวจสอบความสมดุล -----------------------------------------------------
balance <- assigned %>% group_by(wave) %>%
  summarise(
    n            = n(),
    นักเรียนเฉลี่ย  = round(mean(students), 1),
    ห้องเรียนเฉลี่ย = round(mean(classrooms), 1),
    นร_ต่อห้อง     = round(mean(students / classrooms), 2),
    สัดส่วนยากจน   = round(mean(poverty_rate), 3),
    คะแนนฐาน      = round(mean(baseline_score, na.rm = TRUE), 3),
    ขาดครู_pct    = round(mean(short_staff == "ขาดครู"), 3)
  )
print(balance)

# ---- 6) บันทึกผล -------------------------------------------------------------
out <- assigned %>% select(school_id, school_name, esa, stratum, wave) %>%
  arrange(wave, esa, school_id)
write.csv(out, "wave_assignment_FINAL.csv", row.names = FALSE, fileEncoding = "UTF-8")

cat("\n✅ สุ่มเสร็จสิ้น · seed =", SEED,
    "· จำนวนโรงเรียน =", nrow(out), "\n")
cat("🔒 แฮชของไฟล์ผลลัพธ์:",
    tools::md5sum("wave_assignment_FINAL.csv"), "\n")