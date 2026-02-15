require 'yaml'
require 'fileutils'

BASE_DIR   = File.expand_path(File.dirname(__FILE__))
DATA_FILE  = File.join(BASE_DIR, '_data', 'talents.yml')
OUTPUT_DIR = File.join(BASE_DIR, '_talents')

abort("talents.yml not found") unless File.exist?(DATA_FILE)

talents = YAML.load_file(DATA_FILE)
FileUtils.mkdir_p(OUTPUT_DIR)

# ① 既存ページ削除（完全同期）
Dir.glob(File.join(OUTPUT_DIR, "*.md")).each do |file|
  File.delete(file)
end

talents.each do |talent|

  # slug生成（kana優先）
  base = talent['kana'] || talent['name']
  slug = base.to_s
             .downcase
             .gsub(/[^\p{Alnum}]+/, '-')
             .gsub(/^-|-$/, '')

  filename = File.join(OUTPUT_DIR, "#{slug}.md")

  File.open(filename, 'w') do |file|
    file.puts "---"
    file.puts "layout: talent-single"
    file.puts "permalink: /talents/#{slug}/"

    # ② YAML内容をそのまま出力
    talent.each do |key, value|
      file.puts "#{key}: #{value.to_yaml.sub(/^---\s*/, '').strip}"
    end

    file.puts "---"
  end

  puts "Synced: #{filename}"
end

puts "Complete synchronization finished."
