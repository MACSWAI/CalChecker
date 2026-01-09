CREATE TABLE IF NOT EXISTS profiles (
  id BIGINT PRIMARY KEY, 
  username TEXT,
  weight FLOAT,
  height FLOAT,
  bmi FLOAT,
  bmi_category TEXT,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS calorie_logs (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT REFERENCES profiles(id) ON DELETE CASCADE,
  food_name TEXT,
  calories INTEGER,
  protein FLOAT,
  carbs FLOAT,
  fat FLOAT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Matikan RLS agar Mini App bisa akses via Anon Key dengan filter .eq()
ALTER TABLE profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE calorie_logs DISABLE ROW LEVEL SECURITY;