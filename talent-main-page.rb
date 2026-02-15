require 'yaml'
require 'fileutils'

# -----------------------------
# パス設定
# -----------------------------
BASE_DIR   = File.expand_path(File.dirname(__FILE__))
DATA_FILE  = File.join(BASE_DIR, '_data', 'talents.yml')
OUTPUT_DIR = File.join(BASE_DIR, '_talents')

abort("Error: #{DATA_FILE} not found") unless File.exist?(DATA_FILE)

# -----------------------------
# YAMLロード
# -----------------------------
puts "Loading YAML file: #{DATA_FILE}"
talents = YAML.load_file(DATA_FILE)

# nilチェックを追加
if talents.nil?
  abort("Error: #{DATA_FILE} returned nil")
end

unless talents.is_a?(Array)
  abort("Error: #{DATA_FILE} is not an array. Got: #{talents.class}")
end

puts "Loaded #{talents.size} talents"

# -----------------------------
# 出力ディレクトリ作成・初期化
# -----------------------------
FileUtils.mkdir_p(OUTPUT_DIR)
Dir.glob(File.join(OUTPUT_DIR, "*.md")).each { |f| FileUtils.rm_f(f) }

# -----------------------------
# 個別ページ生成
# -----------------------------
talents.each_with_index do |talent, index|
  puts "Processing talent ##{index + 1}: #{talent.inspect[0..100]}"
  
  # talentがnilまたはHashでない場合はスキップ
  unless talent.is_a?(Hash)
    puts "  Skipping: not a Hash"
    next
  end
  
  # slug生成
  base = talent['kana'] || talent['name'] || "unknown"
  slug = base.to_s.downcase.gsub(/[^\p{Alnum}]+/, '-').gsub(/^-|-$/, '')

  filename = File.join(OUTPUT_DIR, "#{slug}.md")

  File.open(filename, 'w') do |file|
    file.puts "---"
    file.puts "layout: talent-single"
    file.puts "permalink: /talents/#{slug}/"

    # 全項目を書き出し
    talent.each do |key, value|
      if value.is_a?(Array)
        file.puts "#{key}:"
        value.each { |v| file.puts "  - #{v}" }
      elsif !value.nil?
        file.puts "#{key}: #{value}"
      end
    end

    file.puts "---"
  end

  puts "  ✓ Synced: #{filename}"
end

puts "\n✓ Complete synchronization finished. Total: #{talents.size} files"