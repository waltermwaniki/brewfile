class Brewfile < Formula
  include Language::Python::Virtualenv

  desc "Intelligent Homebrew package management using brew bundle with JSON configuration"
  homepage "https://github.com/waltermwaniki/homebrew-brewfile"
  # Using URL just for Homebrew metadata - actual install from PyPI
  url "https://files.pythonhosted.org/packages/source/b/brewfile/brewfile-0.1.1.tar.gz"
  sha256 "f728917a2a874edbd0485c16a4c74aea20ed516dade46d699ad6b5881bac21c8"
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
