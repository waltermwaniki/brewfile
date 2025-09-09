class Brewfile < Formula
  include Language::Python::Virtualenv

  desc "Intelligent Homebrew package management using brew bundle with JSON configuration"
  homepage "https://github.com/waltermwaniki/homebrew-brewfile"
  # Using URL just for Homebrew metadata - actual install from PyPI
  url "https://files.pythonhosted.org/packages/source/b/brewfile/brewfile-0.1.5.tar.gz"
  sha256 "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  license "MIT"
  head "https://github.com/waltermwaniki/homebrew-brewfile.git", branch: "main"

  depends_on "python3"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"brewfile", "--help"
  end
end
