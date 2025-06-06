/* -*- Mode: C++; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set ts=8 sts=2 et sw=2 tw=80: */
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

#ifndef nsGenericHTMLFrameElement_h
#define nsGenericHTMLFrameElement_h

#include "mozilla/Attributes.h"

#include "nsFrameLoader.h"
#include "nsFrameLoaderOwner.h"
#include "nsGenericHTMLElement.h"

namespace mozilla {
class ErrorResult;

namespace dom {
class BrowserParent;
template <typename>
struct Nullable;
class WindowProxyHolder;
class XULFrameElement;
}  // namespace dom
}  // namespace mozilla

#define NS_GENERICHTMLFRAMEELEMENT_IID \
  {0x8190db72, 0xdab0, 0x4d72, {0x94, 0x26, 0x87, 0x5f, 0x5a, 0x8a, 0x2a, 0xe5}}

/**
 * A helper class for frame elements
 */
class nsGenericHTMLFrameElement : public nsGenericHTMLElement,
                                  public nsFrameLoaderOwner {
 public:
  nsGenericHTMLFrameElement(
      already_AddRefed<mozilla::dom::NodeInfo>&& aNodeInfo,
      mozilla::dom::FromParser aFromParser)
      : nsGenericHTMLElement(std::move(aNodeInfo)),
        mSrcLoadHappened(false),
        mNetworkCreated(aFromParser == mozilla::dom::FROM_PARSER_NETWORK) {}

  NS_DECL_ISUPPORTS_INHERITED

  NS_INLINE_DECL_STATIC_IID(NS_GENERICHTMLFRAMEELEMENT_IID)

  // nsIContent
  bool IsHTMLFocusable(mozilla::IsFocusableFlags, bool* aIsFocusable,
                       int32_t* aTabIndex) override;
  nsresult BindToTree(BindContext&, nsINode& aParent) override;
  void UnbindFromTree(UnbindContext&) override;
  void DestroyContent() override;

  nsresult CopyInnerTo(mozilla::dom::Element* aDest);

  int32_t TabIndexDefault() override;

  NS_DECL_CYCLE_COLLECTION_CLASS_INHERITED(nsGenericHTMLFrameElement,
                                           nsGenericHTMLElement)

  void SwapFrameLoaders(mozilla::dom::HTMLIFrameElement& aOtherLoaderOwner,
                        mozilla::ErrorResult& aError);

  void SwapFrameLoaders(mozilla::dom::XULFrameElement& aOtherLoaderOwner,
                        mozilla::ErrorResult& aError);

  void SwapFrameLoaders(nsFrameLoaderOwner* aOtherLoaderOwner,
                        mozilla::ErrorResult& rv);

  /**
   * Helper method to map a HTML 'scrolling' attribute value (which can be null)
   * to a ScrollbarPreference value value.  scrolling="no" (and its synonyms)
   * map to Never, and anything else to Auto.
   */
  static mozilla::ScrollbarPreference MapScrollingAttribute(const nsAttrValue*);

  nsIPrincipal* GetSrcTriggeringPrincipal() const {
    return mSrcTriggeringPrincipal;
  }

 protected:
  virtual ~nsGenericHTMLFrameElement();

  // This doesn't really ensure a frame loader in all cases, only when
  // it makes sense.
  void EnsureFrameLoader();
  void LoadSrc();
  Document* GetContentDocument(nsIPrincipal& aSubjectPrincipal);
  mozilla::dom::Nullable<mozilla::dom::WindowProxyHolder> GetContentWindow();

  virtual void AfterSetAttr(int32_t aNameSpaceID, nsAtom* aName,
                            const nsAttrValue* aValue,
                            const nsAttrValue* aOldValue,
                            nsIPrincipal* aSubjectPrincipal,
                            bool aNotify) override;
  virtual void OnAttrSetButNotChanged(int32_t aNamespaceID, nsAtom* aName,
                                      const nsAttrValueOrString& aValue,
                                      bool aNotify) override;

  nsCOMPtr<nsIPrincipal> mSrcTriggeringPrincipal;

  /**
   * True if we have already loaded the frame's original src
   */
  bool mSrcLoadHappened;

  /**
   * True when the element is created by the parser using the
   * NS_FROM_PARSER_NETWORK flag.
   * If the element is modified, it may lose the flag.
   */
  bool mNetworkCreated;

  // This flag is only used by <iframe>. See HTMLIFrameElement::
  // FullscreenFlag() for details. It is placed here so that we
  // do not bloat any struct.
  bool mFullscreenFlag = false;

  /**
   * Represents the iframe is deferred loading until this element gets visible.
   * We just do not load if set and leave specific elements to set it (see
   * HTMLIFrameElement).
   */
  bool mLazyLoading = false;

 private:
  void GetManifestURL(nsAString& aOut);

  /**
   * This function is called by AfterSetAttr and OnAttrSetButNotChanged.
   * It will be called whether the value is being set or unset.
   *
   * @param aNamespaceID the namespace of the attr being set
   * @param aName the localname of the attribute being set
   * @param aValue the value being set or null if the value is being unset
   * @param aNotify Whether we plan to notify document observers.
   */
  void AfterMaybeChangeAttr(int32_t aNamespaceID, nsAtom* aName,
                            const nsAttrValueOrString* aValue,
                            nsIPrincipal* aMaybeScriptedPrincipal,
                            bool aNotify);

  mozilla::dom::BrowsingContext* GetContentWindowInternal();
};

#endif  // nsGenericHTMLFrameElement_h
