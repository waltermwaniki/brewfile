class Brewfile < Formula
  include Language::Python::Virtualenv

  desc "Intelligent Homebrew package management using brew bundle with JSON configuration"
  homepage "https://github.com/waltermwaniki/homebrew-brewfile"
  # Using URL just for Homebrew metadata - actual install from PyPI
  url "https://files.pythonhosted.org/packages/source/b/brewfile/brewfile-0.1.4.tar.gz"
  sha256 "a03ef3861d95b329ff788495b4568c17a549d1f38481ca447ad528714ffc3c14"
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
