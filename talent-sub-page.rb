require 'yaml'
require 'fileutils'

talents = YAML.load_file("_data/talents.yml")
output_dir = "_talents"
FileUtils.mkdir_p(output_dir)

talents.each do |talent|
  slug = talent['slug'] || talent['name'].downcase.strip.gsub(' ', '-')
  filename = "#{output_dir}/#{slug}.md"

  images = talent['images'] || []
  past_projects = talent['past_projects'] || []
  tags = talent['tags'] || []

  social = talent['social'] || {}
  # nilの場合は空文字にする
  instagram = social['instagram'] || ""
  x_account = social['x'] || ""

  front_matter = {
    "layout" => "talent-single",
    "permalink" => "/talents/#{slug}/",
    "name" => talent['name'],
    "kana" => talent['kana'],
    "gender" => talent['gender'],
    "age" => talent['age'],
    "height" => talent['height'],
    "birthplace" => talent['birthplace'],
    "university" => talent['university'],
    "career" => talent['career'],
    "tags" => tags,
    "images" => images,
    "past_projects" => past_projects,
    "social" => {
      "instagram" => instagram,
      "x" => x_account
    }
  }

  File.open(filename, "w") do |file|
    file.puts "---"
    file.puts front_matter.to_yaml.lines[1..-1].join
    file.puts "---"
  end
end

puts "個別ページの生成が完了しました（#{talents.size} 件）"
