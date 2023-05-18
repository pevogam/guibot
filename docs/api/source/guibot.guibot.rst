guibot.guibot module
====================

.. automodule:: guibot.guibot
   :members:
   :undoc-members:
   :show-inheritance:

Retaking image targets
----------------------

Enable automatic retaking while running an existing automation script against
an updated OS or application::

    from guibot.config import GlobalConfig
    from guibot.guibot import GuiBot

    GlobalConfig.retake_images = True
    bot = GuiBot()
    bot.add_path("targets")
    bot.click("button")

Normal searches first use the configured finder and similarity. If an image
target fails to match, guibot gradually lowers that similarity in steps of
``GlobalConfig.retake_similarity_step`` (0.033 by default), stopping at the first
successful level. ``GlobalConfig.retake_similarity`` (0.69 by default) is a hard
lower bound and is always tried if higher levels fail. At the successful level,
guibot chooses the candidate with the highest reported similarity and crops its
replacement pixels. Every attempt and the crop use the same captured screenshot,
without waiting or capturing the screen again.

The replacement updates the original target image file, the live image object,
and its cache entry, so subsequent searches and runs use the new image. Matching
settings are preserved. Images created only in memory are updated in memory.
If no candidate meets the minimum similarity, the usual timeout and failure
behavior applies. A configured similarity already at or below the minimum is
used as-is.

The flag is disabled by default. It applies to all regions and operations that
find targets, including clicks, waits, and the simple and proxy interfaces.
Text and other non-image targets retain their normal matching behavior.
